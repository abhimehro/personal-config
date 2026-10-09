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
import pr_lifecycle_dispositions as dispositions
import pr_lifecycle_ledger_cas as cas
from pr_identity import classify_pr_identity, identity_policy_from_config
from pr_lifecycle_config import validate_config
from pr_lifecycle_issue_status import (
    _BacklogSpec,
    _find_backlog_issue,
    _list_backlog_rows,
    _previous_state,
    backlog_issue_body,
    update_backlog_issue,
)
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
    _RouteArgs,
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


def _comment_items(payload: list[Any]) -> list[Any]:
    """Flatten a --slurp page-of-lists payload, or return it unchanged."""
    if all(isinstance(page, list) for page in payload):
        return [comment for page in payload for comment in page]
    return payload


def _flatten_comment_pages(payload: Any) -> list[dict[str, Any]]:
    """Return comment dicts from a --slurp payload (pages or a flat list)."""
    if not isinstance(payload, list):
        raise TypeError("malformed comments payload")
    raw = _comment_items(payload)
    if not all(isinstance(comment, dict) for comment in raw):
        raise ValueError("malformed comments payload")
    return raw


def _optional_str(value: Any) -> bool:
    """True for None or a string value."""
    return value is None or isinstance(value, str)


def _valid_rest_comment(comment: dict[str, Any]) -> bool:
    """Require a dict user with string login plus optional string fields."""
    author = comment.get("user")
    return (
        isinstance(author, dict)
        and isinstance(author.get("login"), str)
        and _optional_str(comment.get("body"))
        and _optional_str(comment.get("created_at"))
    )


def _normalize_rest_comment(comment: dict[str, Any]) -> dict[str, Any]:
    """Validate one REST comment and return it in inventory shape."""
    if not _valid_rest_comment(comment):
        raise ValueError("malformed comment")
    author = comment["user"]
    body = comment.get("body")
    created_at = comment.get("created_at")
    return {
        "author": {"login": author.get("login") or ""},
        "body": body or "",
        "createdAt": created_at,
    }


def _comment_target_valid(repository: Any, number: Any) -> bool:
    """Require a non-empty repo string and a positive int PR number."""
    return (
        isinstance(repository, str)
        and bool(repository)
        and isinstance(number, int)
        and not isinstance(number, bool)
        and number >= 1
    )


def _comment_backlog_target(pr: dict[str, Any]) -> tuple[str, int] | None:
    """Return the (repository, number) fetch target, or None when invalid."""
    repository = pr.get("repository")
    number = pr.get("number")
    if not _comment_target_valid(repository, number):
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
    if not _comments_total_valid(total_count):
        pr["comments_incomplete"] = True
        return
    if total_count <= len(comments):
        return
    target = _comment_backlog_target(pr)
    if target is None:
        pr["comments_incomplete"] = True
        return
    try:
        pr["comments"] = _normalized_rest_comments(target, total_count, run=run)
    except (
        OSError,
        subprocess.SubprocessError,
        json.JSONDecodeError,
        TypeError,
        ValueError,
    ):
        pr["comments_incomplete"] = True
        return
    pr.pop("comments_incomplete", None)


def _normalized_rest_comments(
    target: tuple[str, int], total_count: int, *, run: Any
) -> list[dict[str, Any]]:
    """Fetch and validate the full comment history for one PR."""
    raw = _fetch_rest_comments(target[0], target[1], run=run)
    if len(raw) < total_count:
        raise ValueError("incomplete comments payload")
    return [_normalize_rest_comment(comment) for comment in raw]


def _comments_total_valid(total_count: Any) -> bool:
    """Require a non-negative int total so fetch counts are trustworthy."""
    return (
        isinstance(total_count, int)
        and not isinstance(total_count, bool)
        and total_count >= 0
    )


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


def _scan_repo(scan: _ScanSpec, *, run: Any) -> tuple[list[dict[str, Any]], int]:
    """Route every fetched PR in a repo; return (actions, comment-fetch count)."""
    actions: list[dict[str, Any]] = []
    fetched = 0
    for pr in scan.prs:
        if _is_excluded(scan.repo, pr, scan.exclusions):
            continue
        fetched += int(_needs_comment_fetch(pr))
        _load_full_comments(pr, run=run)
        verdict = classify_pr_identity(pr, scan.policy)
        actions.extend(
            route_pr(
                pr,
                _RouteArgs(
                    author_type=verdict.author_type,
                    ledger_items_for_pr=_matching_ledger_items(
                        scan.repo, pr, scan.ledger
                    ),
                    ledger=scan.ledger,
                    settings=scan.settings,
                    now=datetime.now(timezone.utc),
                ),
            )
        )
    return actions, fetched


@dataclass(frozen=True)
class _ScanSpec:
    """The per-repo scan inputs: PRs plus shared ledger, policy, settings."""

    repo: str
    prs: list[dict[str, Any]]
    ledger: dict[str, Any]
    policy: Any
    settings: dict[str, Any]
    exclusions: frozenset[tuple[str | None, int]] = frozenset()


def _is_excluded(
    repo: str, pr: dict[str, Any], exclusions: frozenset[tuple[str | None, int]]
) -> bool:
    """True when (repo, number) matches a repo-scoped or number-only exclusion."""
    number = pr.get("number")
    if not isinstance(number, int) or isinstance(number, bool):
        return False
    repo_lc = repo.lower()
    repo_short = repo_lc.rsplit("/", 1)[-1]
    return any(
        number == excl_number
        and (excl_repo is None or excl_repo in (repo_lc, repo_short))
        for excl_repo, excl_number in exclusions
    )


def _normalize_exclusion(raw: Any) -> tuple[str | None, int]:
    """Parse an exclusion spec into (repo_or_none, pr_number).

    Accepted forms: ``owner/repo#123``, ``repo#123``, ``#123``, ``123``.
    A repo-less form matches that PR number in every scanned repository.
    """
    if not isinstance(raw, str):
        raise TypeError("exclusion entries must be strings")
    text = raw.strip()
    if "#" in text:
        repo_part, _, num_part = text.partition("#")
    else:
        repo_part, num_part = "", text
    num_part = num_part.strip()
    if not num_part.isdigit():
        raise ValueError(f"invalid exclusion PR number: {raw}")
    repo = repo_part.strip().lower() or None
    return repo, int(num_part)


def _normalized_exclusions(*groups: Any) -> frozenset[tuple[str | None, int]]:
    """Merge CLI and config exclusion specs into one normalized set."""
    specs = [spec for group in groups for spec in (group or [])]
    return frozenset(_normalize_exclusion(spec) for spec in specs)


def _apply_mutations(
    actions: list[dict[str, Any]], cap: int, apply: bool
) -> tuple[list[dict[str, Any]], int, int]:
    """Select up to cap mutating actions; apply them when apply is true.

    Return (deferred_by_cap, mutations_selected, mutations_unconfirmed); the
    unconfirmed count only grows in apply mode for failed commands or closes
    whose CLOSED state could not be confirmed. Applied actions receive step
    results in place.
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


def _one_decision_issue(spec: _IssueSpec) -> dict[str, Any]:
    """Update one repo's decision issue, or render its dry-run body."""
    rows = _rows_for_repo(spec.repo, spec.actions, spec.ledger, spec.days)
    if not spec.apply or not spec.decision_issues:
        result: dict[str, Any] = {
            "row_count": len(rows),
            "body": backlog_issue_body(_BacklogSpec(spec.repo, {}, spec.now), rows),
        }
        if spec.apply:
            result["action"] = "ISSUE_UPDATE_SKIPPED"
            result["reason"] = "DECISION_ISSUES_FLAG_OFF"
        return result
    tick_outcome = _execute_ticks(spec.repo, spec.ledger, spec.run)
    result: dict[str, Any]
    try:
        result = update_backlog_issue(
            spec.repo,
            rows,
            now=spec.now,
            notify_overdue=spec.overdue_notifications,
        )
    except (OSError, subprocess.SubprocessError) as exc:
        result = {
            "action": "ISSUE_UPDATE_FAILED",
            "repository": spec.repo,
            "reason": type(exc).__name__,
        }
    if tick_outcome is not None:
        result["ticks"] = tick_outcome
    return result


@dataclass(frozen=True)
class _IssueSpec:
    """The per-repo decision-issue inputs plus run mode and timestamp."""

    repo: str
    actions: list[dict[str, Any]]
    ledger: dict[str, Any]
    days: int
    apply: bool
    now: datetime
    decision_issues: bool = False
    overdue_notifications: bool = False
    run: Any = subprocess.run


def _issue_skipped(repo: str) -> dict[str, Any]:
    """Return the skipped-decision-issue payload for an inventory failure."""
    return {
        "action": "ISSUE_UPDATE_SKIPPED",
        "repository": repo,
        "reason": "INVENTORY_FAILED",
    }


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


@dataclass(frozen=True)
class _UnblockArgs:
    """The run_unblock CLI inputs: mode, filters, cap, and runner."""

    apply: bool
    json_out: bool
    repos_filter: list[str] | None
    limit: int | None
    exclusions: tuple[str, ...] = ()
    decision_issues: bool = False
    overdue_notifications: bool = False
    run: Any = subprocess.run


def run_unblock(unblock_args: _UnblockArgs) -> int:
    """Build and emit a blocker plan, applying bounded mutations when requested.

    Fetch the ledger and open PR inventory, classify identities, and route
    blockers. In apply mode, bounded PR mutations run by default; decision
    issues refresh only when decision_issues is set, and overdue @-mention
    comments only when overdue_notifications is set — both render into the
    plan either way. Return zero after emitting the plan.

    limit caps PR mutation proposals, defaults to stage1_actions, and leaves
    overflow in deferred_by_cap. Excluded PRs get no actions at all; ledger
    items owned by human/stage2/stage3 keep only escalation rows. Inventory
    and issue-update failures become plan entries; PR command failures are
    recorded on actions. Configuration and ledger fetch errors propagate;
    unknown repository filters raise ValueError.
    """
    config = load_yaml(ROOT / "tasks/pr-review-agent.config.yaml")
    validate_config(config)
    repositories = _resolve_repositories(config, unblock_args.repos_filter)
    lifecycle = config["lifecycle"]
    settings = lifecycle.get("unblock") or {}
    cap = unblock_args.limit
    if cap is None:
        cap = lifecycle["stage_caps"]["stage1_actions"]
    plan = _scan_and_plan(
        _ScanPlanSpec(unblock_args, config, repositories, lifecycle, settings, cap)
    )
    _emit(plan, unblock_args.json_out)
    return 0


@dataclass(frozen=True)
class _ScanPlanSpec:
    """Everything _scan_and_plan needs, folded to respect the arg-count gate."""

    unblock_args: _UnblockArgs
    config: dict[str, Any]
    repositories: list[str]
    lifecycle: dict[str, Any]
    settings: dict[str, Any]
    cap: int


def _scan_and_plan(spec: _ScanPlanSpec) -> dict[str, Any]:
    """Fetch the ledger, scan repos, apply mutations, and build the plan."""
    unblock_args = spec.unblock_args
    config = spec.config
    repositories = spec.repositories
    lifecycle = spec.lifecycle
    settings = spec.settings
    cap = spec.cap
    apply = unblock_args.apply
    run = unblock_args.run
    with tempfile.TemporaryDirectory(prefix="pr-lifecycle-unblock-") as tmp:
        fetch = cas.run_preflight(Path(tmp) / "ledger.yaml")
        ledger = load_yaml(Path(fetch["ledger_path"]))
        policy = identity_policy_from_config(config)
        actions, inventory_failed, fetched = _scan_repositories(
            _ScanJob(
                repositories,
                ledger,
                policy,
                settings,
                _normalized_exclusions(
                    unblock_args.exclusions, settings.get("exclusions")
                ),
            ),
            run,
        )
        deferred_by_cap, mutation_count, unconfirmed = _apply_mutations(
            actions, cap, apply
        )
        escalation_issues = _decision_issue_updates(
            _DecisionCtx(
                repositories,
                actions,
                ledger,
                lifecycle,
                inventory_failed,
                apply,
                datetime.now(timezone.utc),
                unblock_args.decision_issues,
                unblock_args.overdue_notifications,
                unblock_args.run,
            )
        )
        return _build_plan(
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
                fetched=fetched,
                escalation_issues=escalation_issues,
            )
        )


@dataclass(frozen=True)
class _ScanJob:
    """The multi-repo scan inputs: repo list plus shared state."""

    repositories: list[str]
    ledger: dict[str, Any]
    policy: Any
    settings: dict[str, Any]
    exclusions: frozenset[tuple[str | None, int]] = frozenset()


def _scan_repositories(
    job: _ScanJob, run: Any
) -> tuple[list[dict[str, Any]], list[dict[str, str]], int]:
    """Scan every repo, returning (actions, inventory failures, fetch count)."""
    actions: list[dict[str, Any]] = []
    inventory_failed: list[dict[str, str]] = []
    fetched_count = 0
    for repo in job.repositories:
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
        scanned, fetched = _scan_repo(
            _ScanSpec(repo, prs, job.ledger, job.policy, job.settings, job.exclusions),
            run=run,
        )
        actions.extend(scanned)
        fetched_count += fetched
    actions.extend(inventory_failed)
    return actions, inventory_failed, fetched_count


@dataclass(frozen=True)
class _DecisionCtx:
    """The decision-issue refresh inputs: repos, shared state, run mode."""

    repositories: list[str]
    actions: list[dict[str, Any]]
    ledger: dict[str, Any]
    lifecycle: dict[str, Any]
    inventory_failed: list[dict[str, str]]
    apply: bool
    now: datetime
    decision_issues: bool = False
    overdue_notifications: bool = False
    run: Any = subprocess.run


def _execute_ticks(
    repo: str, ledger: dict[str, Any], run: Any
) -> dict[str, Any] | None:
    """Execute verified decision-issue ticks before the issue re-renders."""
    try:
        issue = _find_backlog_issue(_list_backlog_rows(repo))
        if not issue:
            return None
        ctx = dispositions.ExecCtx(
            repo, issue, ledger, _previous_state(issue.get("body")), run
        )
        outcome = dispositions.execute(ctx)
    except (OSError, subprocess.SubprocessError) as exc:
        outcome = {"accepted": [], "skipped": [], "reason": type(exc).__name__}
    if outcome.get("reason") or outcome.get("skipped"):
        detail = outcome.get("reason") or [s.get("skipped") for s in outcome["skipped"]]
        print(f"decision-issue ticks for {repo}: {detail}", file=sys.stderr)
    return outcome


def _decision_issue_updates(ctx: _DecisionCtx) -> dict[str, Any]:
    """Refresh per-repo decision issues, skipping repos whose inventory failed."""
    packet_expiry_days = ctx.lifecycle.get("packet_expiry_close_days", 7)
    if not isinstance(packet_expiry_days, int) or packet_expiry_days < 1:
        packet_expiry_days = 7
    failed_repos = {
        entry["repository"] for entry in ctx.inventory_failed if entry.get("repository")
    }
    results: dict[str, Any] = {}
    for repo in ctx.repositories:
        if repo in failed_repos:
            results[repo] = _issue_skipped(repo)
            continue
        results[repo] = _one_decision_issue(
            _IssueSpec(
                repo,
                ctx.actions,
                ctx.ledger,
                packet_expiry_days,
                ctx.apply,
                ctx.now,
                ctx.decision_issues,
                ctx.overdue_notifications,
                ctx.run,
            )
        )
    return results


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
    parser.add_argument(
        "--exclude",
        action="append",
        default=[],
        metavar="REPO#PR",
        help=(
            "exclude a PR from every routing action; accepts owner/repo#123, "
            "repo#123, #123, or 123 (repo-less forms match that number in "
            "every scanned repository)"
        ),
    )
    parser.add_argument(
        "--decision-issues",
        action="store_true",
        help=(
            "with --apply, also create or refresh the per-repo human "
            "decision issues; without it apply only runs bounded mutations "
            "and renders the issue bodies into the plan"
        ),
    )
    parser.add_argument(
        "--overdue-notifications",
        action="store_true",
        help=(
            "with --apply and --decision-issues, also post the @-mention "
            "comments for newly overdue decision rows"
        ),
    )
    return parser


def main(argv: list[str] | None = None) -> int:
    """Run the unblock CLI, returning one for invalid limits or handled failures."""
    args = build_parser().parse_args(argv)
    if args.limit is not None and args.limit < 0:
        print("PR_LIFECYCLE_UNBLOCK_ERROR: ValueError", file=sys.stderr)
        return 1
    try:
        return run_unblock(
            _UnblockArgs(
                apply=args.apply,
                json_out=args.json_out,
                repos_filter=args.repos_filter,
                limit=args.limit,
                exclusions=tuple(args.exclude),
                decision_issues=args.decision_issues,
                overdue_notifications=args.overdue_notifications,
            )
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
