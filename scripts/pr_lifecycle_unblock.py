#!/usr/bin/env python3
"""Route live PR blockers to bounded fixes or explicit human decisions.

Dry-run by default. GitHub mutations require ``--apply`` and never merge or
delete branches. Routing decisions live in pr_lifecycle_unblock_routing,
bounded GitHub mutations in pr_lifecycle_unblock_apply, and backlog rows in
pr_lifecycle_unblock_rows; this module wires them into the CLI plan.
"""

from __future__ import annotations

import argparse
import json
import subprocess
import sys
import tempfile
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

SCRIPT_DIR = Path(__file__).resolve().parent
if str(SCRIPT_DIR) not in sys.path:
    sys.path.insert(0, str(SCRIPT_DIR))

# pylint: disable=wrong-import-position,unused-import
import pr_lifecycle_ledger_cas as cas
from pr_identity import classify_pr_identity, identity_policy_from_config
from pr_lifecycle_config import validate_config
from pr_lifecycle_issue_status import backlog_issue_body, update_backlog_issue
from pr_lifecycle_open_inventory import list_open_prs
from pr_lifecycle_support import ROOT
from pr_lifecycle_unblock_apply import _MUTATING_ACTIONS, _apply_action
from pr_lifecycle_unblock_routing import (
    _JULES_PREFIXES,  # noqa: F401
    _LINEAGE_RE,  # noqa: F401
    _S2_HANDOFF_PREFIX,  # noqa: F401
    _advisory,  # noqa: F401
    _escalation,  # noqa: F401
    _family,  # noqa: F401
    _iso,  # noqa: F401
    _lineage_date,  # noqa: F401
    _parse_datetime,  # noqa: F401
    _route_review,  # noqa: F401
    _safe_check_names,  # noqa: F401
    _salvage_replacement,  # noqa: F401
    _sticky_security,  # noqa: F401
    _terminal_but_open,  # noqa: F401
    _trigger_action,  # noqa: F401
    _utc,  # noqa: F401
    route_pr,
)
from pr_lifecycle_unblock_rows import (
    _human_ledger_rows,  # noqa: F401
    _repo_counts,
    _rows_for_repo,
)
from pr_lifecycle_yaml import load_yaml

# pylint: enable=wrong-import-position,unused-import


def _fetch_rest_comments(
    repository: str, number: int, *, run: Any
) -> list[dict[str, Any]]:
    """Fetch all REST issue comments, flattening --slurp page arrays.

    Raise OSError for a nonzero exit and ValueError/TypeError for malformed
    or mixed-shape payloads; process launch errors and timeouts propagate.
    """
    result = run(
        [
            "gh",
            "api",
            "--paginate",
            "--slurp",
            f"repos/{repository}/issues/{number}/comments",
        ],
        check=False,
        capture_output=True,
        text=True,
        timeout=60,
    )
    if result.returncode != 0:
        raise OSError(f"gh api comments failed rc={result.returncode}")
    return _flatten_comment_pages(json.loads(result.stdout))


def _flatten_comment_pages(payload: Any) -> list[dict[str, Any]]:
    """Return comment dicts from a --slurp payload (pages or a flat list)."""
    if not isinstance(payload, list):
        raise TypeError("malformed comments payload")
    if all(isinstance(page, list) for page in payload):
        raw = [comment for page in payload for comment in page]
    elif all(isinstance(comment, dict) for comment in payload):
        raw = payload
    else:
        raise ValueError("malformed comments payload")
    if not all(isinstance(comment, dict) for comment in raw):
        raise ValueError("malformed comments payload")
    return raw


def _normalize_rest_comment(comment: dict[str, Any]) -> dict[str, Any]:
    """Validate one REST comment and return it in inventory shape."""
    author = comment.get("user")
    body = comment.get("body")
    created_at = comment.get("created_at")
    if (
        not isinstance(author, dict)
        or not isinstance(author.get("login"), str)
        or (body is not None and not isinstance(body, str))
        or (created_at is not None and not isinstance(created_at, str))
    ):
        raise ValueError("malformed comment")
    return {
        "author": {"login": author.get("login") or ""},
        "body": body or "",
        "createdAt": created_at,
    }


def _comment_backlog_target(pr: dict[str, Any]) -> tuple[str, int] | None:
    """Return the (repository, number) fetch target, or None when invalid."""
    repository = pr.get("repository")
    number = pr.get("number")
    if (
        not isinstance(repository, str)
        or not repository
        or not isinstance(number, int)
        or isinstance(number, bool)
        or number < 1
    ):
        return None
    return repository, number


def _load_full_comments(pr: dict[str, Any], *, run: Any) -> None:
    """Fill missing PR comment history in place using paginated GitHub results.

    Set comments_incomplete when counts are unknown or fetching or validation
    fails, so callers cannot issue triggers without verified deduplication.
    """
    comments = pr.get("comments")
    if not isinstance(comments, list):
        comments = []
        pr["comments"] = comments
    total_count = pr.get("commentsTotalCount")
    if (
        not isinstance(total_count, int)
        or isinstance(total_count, bool)
        or total_count < 0
    ):
        pr["comments_incomplete"] = True
        return
    if total_count <= len(comments):
        return
    target = _comment_backlog_target(pr)
    if target is None:
        pr["comments_incomplete"] = True
        return
    try:
        raw = _fetch_rest_comments(target[0], target[1], run=run)
        if len(raw) < total_count:
            raise ValueError("incomplete comments payload")
        normalized = [_normalize_rest_comment(comment) for comment in raw]
    except (
        OSError,
        subprocess.SubprocessError,
        json.JSONDecodeError,
        TypeError,
        ValueError,
    ):
        pr["comments_incomplete"] = True
        return
    pr["comments"] = normalized
    pr.pop("comments_incomplete", None)


def _resolve_repositories(
    config: dict[str, Any], repos_filter: list[str] | None
) -> list[str]:
    """Return configured repos narrowed by the filter; raise for unknown names."""
    repositories = list(config["repos"])
    if repos_filter:
        unknown = sorted(set(repos_filter) - set(repositories))
        if unknown:
            raise ValueError(f"unknown repository filter: {', '.join(unknown)}")
        repositories = [repo for repo in repositories if repo in set(repos_filter)]
    return repositories


def _needs_comment_fetch(pr: dict[str, Any]) -> bool:
    """True when the inventory page holds fewer comments than the total count."""
    comments = pr.get("comments")
    comment_count = len(comments) if isinstance(comments, list) else 0
    total_count = pr.get("commentsTotalCount")
    return (
        isinstance(total_count, int)
        and not isinstance(total_count, bool)
        and total_count > comment_count
    )


def _matching_ledger_items(
    repo: str, pr: dict[str, Any], ledger: dict[str, Any]
) -> list[dict[str, Any]]:
    """Return ledger items whose repository and pr number match this PR."""
    return [
        item
        for item in ledger.get("items") or []
        if isinstance(item, dict)
        and item.get("repository") == repo
        and item.get("pr") == pr.get("number")
    ]


def _scan_repo(
    repo: str,
    prs: list[dict[str, Any]],
    ledger: dict[str, Any],
    policy: Any,
    settings: dict[str, Any],
    *,
    run: Any,
) -> tuple[list[dict[str, Any]], int]:
    """Route every fetched PR in a repo; return (actions, comment-fetch count)."""
    actions: list[dict[str, Any]] = []
    fetched = 0
    for pr in prs:
        fetched += int(_needs_comment_fetch(pr))
        _load_full_comments(pr, run=run)
        verdict = classify_pr_identity(pr, policy)
        actions.extend(
            route_pr(
                pr,
                author_type=verdict.author_type,
                ledger_items_for_pr=_matching_ledger_items(repo, pr, ledger),
                ledger=ledger,
                settings=settings,
                now=datetime.now(timezone.utc),
            )
        )
    return actions, fetched


def _apply_mutations(
    actions: list[dict[str, Any]], cap: int, apply: bool
) -> tuple[list[dict[str, Any]], int, int]:
    """Select up to cap mutating actions; apply them when apply is true.

    Return (deferred_by_cap, mutations_selected, mutations_unconfirmed); the
    unconfirmed count only grows in apply mode for steps GitHub rejected.
    """
    deferred_by_cap: list[dict[str, Any]] = []
    mutation_count = 0
    unconfirmed = 0
    for action in actions:
        if action.get("action") not in _MUTATING_ACTIONS:
            continue
        if mutation_count >= cap:
            deferred_by_cap.append(action)
            continue
        mutation_count += 1
        if apply:
            _apply_action(action)
            unconfirmed += bool(action.get("unconfirmed"))
    return deferred_by_cap, mutation_count, unconfirmed


def _one_decision_issue(
    repo: str,
    actions: list[dict[str, Any]],
    ledger: dict[str, Any],
    packet_expiry_days: int,
    *,
    apply: bool,
    now: datetime,
) -> dict[str, Any]:
    """Update one repo's decision issue, or render its dry-run body."""
    rows = _rows_for_repo(repo, actions, ledger, packet_expiry_days)
    if not apply:
        return {
            "row_count": len(rows),
            "body": backlog_issue_body(repo, rows, {}, now),
        }
    try:
        return update_backlog_issue(repo, rows, now=now)
    except (OSError, subprocess.SubprocessError) as exc:
        return {
            "action": "ISSUE_UPDATE_FAILED",
            "repository": repo,
            "reason": type(exc).__name__,
        }


def _update_decision_issues(
    repositories: list[str],
    actions: list[dict[str, Any]],
    ledger: dict[str, Any],
    failed_repos: set[str],
    packet_expiry_days: int,
    *,
    apply: bool,
    now: datetime,
) -> dict[str, Any]:
    """Refresh each repo's decision issue, or skip when inventory failed."""
    escalation_issues: dict[str, Any] = {}
    for repo in repositories:
        if repo in failed_repos:
            escalation_issues[repo] = {
                "action": "ISSUE_UPDATE_SKIPPED",
                "repository": repo,
                "reason": "INVENTORY_FAILED",
            }
            continue
        escalation_issues[repo] = _one_decision_issue(
            repo,
            actions,
            ledger,
            packet_expiry_days,
            apply=apply,
            now=now,
        )
    return escalation_issues


@dataclass(frozen=True)
class _PlanFields:
    """Inputs assembled into the emitted unblock plan payload."""

    apply: bool
    ledger: dict[str, Any]
    repositories: list[str]
    actions: list[dict[str, Any]]
    deferred_by_cap: list[dict[str, Any]]
    cap: int
    mutation_count: int
    unconfirmed: int
    inventory_failed: list[dict[str, str]]
    fetched: int
    escalation_issues: dict[str, Any]


def _build_plan(plan: _PlanFields) -> dict[str, Any]:
    """Assemble the emitted unblock plan payload."""
    return {
        "dry_run": not plan.apply,
        "ledger_revision": plan.ledger.get("ledger_revision"),
        "repositories": _repo_counts(plan.actions, plan.repositories),
        "action_count": len(plan.actions),
        "actions": plan.actions,
        "deferred_by_cap": plan.deferred_by_cap,
        "deferred_by_cap_count": len(plan.deferred_by_cap),
        "mutation_cap": plan.cap,
        "mutations_selected": plan.mutation_count,
        "mutations_applied": (
            plan.mutation_count - plan.unconfirmed if plan.apply else 0
        ),
        "mutations_unconfirmed": plan.unconfirmed if plan.apply else 0,
        "inventory_failed": plan.inventory_failed,
        "comment_history_fetch_pr_count": plan.fetched,
        "escalation_issues": plan.escalation_issues,
    }


def run_unblock(
    *,
    apply: bool,
    json_out: bool,
    repos_filter: list[str] | None,
    limit: int | None,
    run: Any = subprocess.run,
) -> int:
    """Build and emit a blocker plan, applying bounded mutations when requested.

    Fetch the ledger and open PR inventory, classify identities, and route
    blockers. In apply mode, refresh decision issues only for repositories
    whose inventory succeeded. Return zero after emitting the plan.

    limit caps PR mutation proposals, defaults to stage1_actions, and leaves
    overflow in deferred_by_cap. Decision issue updates are outside this cap.
    Inventory and issue-update failures become plan entries; PR command
    failures are recorded on actions. Configuration and ledger fetch errors
    propagate; unknown repository filters raise ValueError.
    """
    config = load_yaml(ROOT / "tasks/pr-review-agent.config.yaml")
    validate_config(config)
    repositories = _resolve_repositories(config, repos_filter)
    lifecycle = config["lifecycle"]
    settings = lifecycle.get("unblock") or {}
    cap = limit
    if cap is None:
        cap = lifecycle["stage_caps"]["stage1_actions"]
    with tempfile.TemporaryDirectory(prefix="pr-lifecycle-unblock-") as tmp:
        fetch = cas.run_preflight(Path(tmp) / "ledger.yaml")
        ledger = load_yaml(Path(fetch["ledger_path"]))
        actions: list[dict[str, Any]] = []
        inventory_failed: list[dict[str, str]] = []
        comment_history_fetch_pr_count = 0
        policy = identity_policy_from_config(config)
        for repo in repositories:
            try:
                prs = list_open_prs(repo)
            except OSError as exc:
                inventory_failed.append(
                    {
                        "action": "INVENTORY_FAILED",
                        "repository": repo,
                        "reason": f"{type(exc).__name__}: {exc}"[:200],
                    }
                )
                continue
            scanned, fetched = _scan_repo(repo, prs, ledger, policy, settings, run=run)
            actions.extend(scanned)
            comment_history_fetch_pr_count += fetched
        actions.extend(inventory_failed)
        deferred_by_cap, mutation_count, unconfirmed = _apply_mutations(
            actions, cap, apply
        )
        now = datetime.now(timezone.utc)
        packet_expiry_days = lifecycle.get("packet_expiry_close_days", 7)
        if not isinstance(packet_expiry_days, int) or packet_expiry_days < 1:
            packet_expiry_days = 7
        failed_repos = {
            entry["repository"] for entry in inventory_failed if entry.get("repository")
        }
        escalation_issues = _update_decision_issues(
            repositories,
            actions,
            ledger,
            failed_repos,
            packet_expiry_days,
            apply=apply,
            now=now,
        )
        plan = _build_plan(
            _PlanFields(
                apply=apply,
                ledger=ledger,
                repositories=repositories,
                actions=actions,
                deferred_by_cap=deferred_by_cap,
                cap=cap,
                mutation_count=mutation_count,
                unconfirmed=unconfirmed,
                inventory_failed=inventory_failed,
                fetched=comment_history_fetch_pr_count,
                escalation_issues=escalation_issues,
            )
        )
        _emit(plan, json_out)
    return 0


def _emit(plan: dict[str, Any], json_out: bool) -> None:
    """Print the unblock plan as JSON or a brief action and deferral summary."""
    if json_out:
        print(json.dumps(plan, indent=2, sort_keys=True))
        return
    print(
        f"PR lifecycle unblock: {plan['action_count']} actions across "
        f"{len(plan['repositories'])} repositories; "
        f"{plan['deferred_by_cap_count']} deferred by cap"
    )


def build_parser() -> argparse.ArgumentParser:
    """Build the unblock CLI parser for apply mode, output, filters, and limits."""
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--apply", action="store_true")
    parser.add_argument("--json", action="store_true", dest="json_out")
    parser.add_argument("--repo", action="append", dest="repos_filter")
    parser.add_argument("--limit", type=int)
    return parser


def main(argv: list[str] | None = None) -> int:
    """Run the unblock CLI, returning one for invalid limits or handled failures."""
    args = build_parser().parse_args(argv)
    if args.limit is not None and args.limit < 0:
        print("PR_LIFECYCLE_UNBLOCK_ERROR: ValueError", file=sys.stderr)
        return 1
    try:
        return run_unblock(
            apply=args.apply,
            json_out=args.json_out,
            repos_filter=args.repos_filter,
            limit=args.limit,
        )
    except (
        OSError,
        subprocess.SubprocessError,
        ValueError,
        KeyError,
        TypeError,
    ) as exc:
        print(f"PR_LIFECYCLE_UNBLOCK_ERROR: {type(exc).__name__}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
