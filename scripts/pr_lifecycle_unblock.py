#!/usr/bin/env python3
"""Route live PR blockers to bounded fixes or explicit human decisions.

Dry-run by default. GitHub mutations require ``--apply`` and never merge or
delete branches.
"""

from __future__ import annotations

import argparse
import json
import re
import subprocess
import sys
import tempfile
from collections import Counter
from datetime import date, datetime, timedelta, timezone
from pathlib import Path
from typing import Any

SCRIPT_DIR = Path(__file__).resolve().parent
if str(SCRIPT_DIR) not in sys.path:
    sys.path.insert(0, str(SCRIPT_DIR))

# pylint: disable=wrong-import-position
import pr_lifecycle_ledger_cas as cas
from pr_identity import classify_pr_identity, identity_policy_from_config
from pr_lifecycle_config import validate_config
from pr_lifecycle_issue_status import backlog_issue_body, update_backlog_issue
from pr_lifecycle_open_inventory import list_open_prs
from pr_lifecycle_support import ROOT
from pr_lifecycle_yaml import load_yaml

_JULES_PREFIXES = (
    "sentinel/",
    "sentinel-",
    "bolt/",
    "bolt-",
    "palette/",
    "palette-",
    "jules-",
)
_LINEAGE_RE = re.compile(r"^pr-lifecycle-docs-(\d{8})")
# Stage 2 ledger handoff event ids mark a salvage replacement's origin.
_S2_HANDOFF_PREFIX = "evt-s2-"
_EXPIRES_RE = re.compile(r"\bExpires\s+(\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}Z)")
_MUTATING_ACTIONS = {
    "CLOSE_STALE_LINEAGE",
    "CLOSE_SUPERSEDED",
    "UPDATE_BRANCH",
    "TRIGGER",
}


def _utc(value: datetime) -> datetime:
    if value.tzinfo is None:
        return value.replace(tzinfo=timezone.utc)
    return value.astimezone(timezone.utc)


def _iso(value: datetime) -> str:
    return _utc(value).strftime("%Y-%m-%dT%H:%M:%SZ")


def _safe_check_names(names: list[str]) -> list[str]:
    safe: list[str] = []
    for name in names[:10]:
        if not isinstance(name, str):
            continue
        cleaned = re.sub(r"[^\w .:/()\-]", "", name)[:80]
        if cleaned:
            safe.append(cleaned)
    return safe


def _parse_datetime(value: object) -> datetime | None:
    if not isinstance(value, str) or not value:
        return None
    try:
        parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
    except ValueError:
        return None
    return _utc(parsed)


def _family(pr: dict[str, Any]) -> str:
    author = pr.get("author")
    login = str(author.get("login") or "").lower() if isinstance(author, dict) else ""
    branch = str(pr.get("headRefName") or "").lower()
    if "dependabot" in login:
        return "dependabot"
    if login == "coderabbitai[bot]" or branch.startswith("coderabbit"):
        return "coderabbit"
    if branch.startswith(_JULES_PREFIXES):
        return "jules"
    if _LINEAGE_RE.match(str(pr.get("headRefName") or "")):
        return "lineage"
    return "other"


def _sticky_security(items: list[dict[str, Any]]) -> bool:
    return any(
        item.get("lifecycle_state") != "TERMINAL"
        and item.get("guardrail_outcome") == "REVIEW_SECURITY"
        for item in items
    )


def _escalation(
    pr: dict[str, Any],
    author_type: str,
    blocker: str,
    *,
    evidence: Any,
    recommended_action: str,
    owner: str = "human",
    security: bool = False,
) -> dict[str, Any]:
    human_or_security = author_type != "BOT" or security or owner == "human"
    return {
        "action": "ESCALATE",
        "repository": pr.get("repository"),
        "pr": pr.get("number"),
        "url": pr.get("url"),
        "head_sha": pr.get("headRefOid"),
        "author_type": author_type,
        "blocker": blocker,
        "evidence": evidence,
        "recommended_action": recommended_action,
        "security": security,
        "safe_default": (
            "Leave open; no merge or close without a human decision."
            if human_or_security
            else "Leave open until the next owner acts."
        ),
        "owner": owner,
    }


def _trigger_action(
    pr: dict[str, Any],
    author_type: str,
    kind: str,
    body: str,
    settings: dict[str, Any],
    now: datetime,
    *,
    blocker: str,
    evidence: Any,
    recommended_action: str,
    family: str,
    sticky_security: bool,
) -> list[dict[str, Any]]:
    if sticky_security or (
        kind != "codescene" and author_type != "BOT" and family != "jules"
    ):
        return [
            _escalation(
                pr,
                author_type,
                blocker,
                evidence=evidence,
                recommended_action=recommended_action,
                security=sticky_security,
            )
        ]
    if pr.get("comments_incomplete"):
        return [
            {
                "action": "TRIGGER_SKIPPED",
                "repository": pr.get("repository"),
                "pr": pr.get("number"),
                "url": pr.get("url"),
                "head_sha": pr.get("headRefOid"),
                "author_type": author_type,
                "kind": kind,
                "reason": "comment history unavailable; marker dedupe unverified",
            }
        ]
    head = str(pr.get("headRefOid") or "")
    marker = f"<!-- pr-lifecycle-trigger kind={kind} head={head} -->"
    matching = [
        comment
        for comment in pr.get("comments") or []
        if isinstance(comment, dict) and marker in str(comment.get("body") or "")
    ]
    if matching:
        comment = matching[-1]
        created = _parse_datetime(comment.get("createdAt"))
        expiry = settings.get("trigger_expiry_days", 3)
        if not isinstance(expiry, int) or isinstance(expiry, bool) or expiry < 1:
            expiry = 3
        if created is None or _utc(now) - created > timedelta(days=expiry):
            sent = comment.get("createdAt") or "unknown date"
            return [
                _escalation(
                    pr,
                    author_type,
                    "trigger_unanswered",
                    evidence={"kind": kind, "sent": sent},
                    recommended_action=(
                        f"trigger {kind} sent {sent} without a new push; decide fix/close"
                    ),
                    security=sticky_security,
                )
            ]
        return []
    return [
        {
            "action": "TRIGGER",
            "repository": pr.get("repository"),
            "pr": pr.get("number"),
            "url": pr.get("url"),
            "head_sha": head,
            "author_type": author_type,
            "kind": kind,
            "body": f"{body.rstrip()}\n\n{marker}",
            "marker": marker,
        }
    ]


def _advisory(name: str, patterns: list[str]) -> bool:
    return any(
        name.startswith(pattern[:-1]) if pattern.endswith("*") else name == pattern
        for pattern in patterns
    )


def _lineage_date(pr: dict[str, Any]) -> date | None:
    match = _LINEAGE_RE.match(str(pr.get("headRefName") or ""))
    if match is None:
        return None
    try:
        return (
            datetime.strptime(match.group(1), "%Y%m%d")
            .replace(tzinfo=timezone.utc)
            .date()
        )
    except ValueError:
        return None


def _salvage_replacement(
    pr: dict[str, Any],
    ledger_items_for_pr: list[dict[str, Any]],
    ledger: dict[str, Any],
) -> dict[str, Any] | None:
    items = [
        item
        for item in (ledger.get("items") or [])
        if isinstance(item, dict) and item.get("lifecycle_state") == "TERMINAL"
    ]
    items.extend(
        item
        for item in ledger_items_for_pr
        if item.get("lifecycle_state") == "TERMINAL" and item not in items
    )
    for replacement in items:
        if not str(replacement.get("terminal_disposition") or "").startswith("MERGED_"):
            continue
        handoffs = replacement.get("handoffs") or []
        evidence_urls = replacement.get("evidence_urls") or []
        if (
            handoffs
            and str(handoffs[0]).startswith(_S2_HANDOFF_PREFIX)
            and replacement.get("url") != pr.get("url")
            and pr.get("url") in evidence_urls
        ):
            return replacement
    return None


def _terminal_but_open(
    pr: dict[str, Any],
    ledger_items_for_pr: list[dict[str, Any]],
    author_type: str,
) -> dict[str, Any] | None:
    if any(item.get("lifecycle_state") != "TERMINAL" for item in ledger_items_for_pr):
        return None
    head = str(pr.get("headRefOid") or "")
    for item in ledger_items_for_pr:
        if item.get("lifecycle_state") == "TERMINAL" and item.get("key") == (
            f"{pr.get('repository')}#{pr.get('number')}@{head}"
        ):
            return _escalation(
                pr,
                author_type,
                "ledger_terminal_but_open",
                evidence={"terminal_disposition": item.get("terminal_disposition")},
                recommended_action=(
                    "PR is open but ledger says "
                    f"{item.get('terminal_disposition')}: close it or confirm it "
                    "should be re-reviewed"
                ),
                owner="human",
                security=item.get("guardrail_outcome") == "REVIEW_SECURITY",
            )
    return None


def route_pr(
    pr: dict[str, Any],
    *,
    author_type: str,
    ledger_items_for_pr: list[dict[str, Any]],
    ledger: dict[str, Any],
    settings: dict[str, Any],
    now: datetime,
) -> list[dict[str, Any]]:
    """Return ordered fix, trigger, advisory, or escalation proposals."""
    family = _family(pr)
    security = _sticky_security(ledger_items_for_pr)
    repo = str(pr.get("repository") or "")
    number = pr.get("number")
    head = str(pr.get("headRefOid") or "")
    base = str(pr.get("baseRefName") or "")
    safe_base = _safe_check_names([base])
    base = safe_base[0] if safe_base else "base branch"
    lineage_stale_days = settings.get("lineage_stale_days", 3)
    if (
        family == "lineage"
        and author_type == "BOT"
        and not security
        and _lineage_date(pr) is not None
        and (_utc(now).date() - _lineage_date(pr)).days > lineage_stale_days
    ):
        age_days = (_utc(now).date() - _lineage_date(pr)).days
        return [
            {
                "action": "CLOSE_STALE_LINEAGE",
                "repository": repo,
                "pr": number,
                "url": pr.get("url"),
                "head_sha": head,
                "author_type": author_type,
                "comment": (
                    f"Closing stale pipeline run-record PR (older than "
                    f"{lineage_stale_days} days); a newer lineage PR / the runtime "
                    "ledger supersedes it. Branch retained — reopen to recover."
                ),
                "age_days": age_days,
            }
        ]

    replacement = _salvage_replacement(pr, ledger_items_for_pr, ledger)
    if replacement is not None:
        replacement_url = str(replacement.get("url") or "")
        if author_type == "BOT" and not security:
            return [
                {
                    "action": "CLOSE_SUPERSEDED",
                    "repository": repo,
                    "pr": number,
                    "url": pr.get("url"),
                    "head_sha": head,
                    "author_type": author_type,
                    "replacement_url": replacement_url,
                    "comment": (
                        f"Superseded by {replacement_url} (merged salvage replacement)."
                    ),
                }
            ]
        return [
            _escalation(
                pr,
                author_type,
                "salvage_replacement_merged",
                evidence={"replacement_url": replacement_url},
                recommended_action=(
                    f"close original as superseded by {replacement_url}"
                ),
                security=security,
            )
        ]

    terminal_open = _terminal_but_open(pr, ledger_items_for_pr, author_type)
    if terminal_open is not None:
        return [terminal_open]

    if pr.get("isDraft"):
        return []

    mergeable = str(pr.get("mergeable") or "").upper()
    merge_state = str(pr.get("mergeStateStatus") or "").upper()
    conflict = mergeable == "CONFLICTING" or merge_state == "DIRTY"
    if conflict:
        if family == "dependabot":
            return _trigger_action(
                pr,
                author_type,
                "dependabot_rebase",
                "@dependabot rebase",
                settings,
                now,
                blocker="merge_conflict",
                evidence={"mergeable": mergeable, "mergeStateStatus": merge_state},
                recommended_action="request a bounded conflict rebase",
                family=family,
                sticky_security=security,
            )
        if family == "coderabbit":
            return _trigger_action(
                pr,
                author_type,
                "coderabbit_conflict",
                "@coderabbitai resolve merge conflict",
                settings,
                now,
                blocker="merge_conflict",
                evidence={"mergeable": mergeable, "mergeStateStatus": merge_state},
                recommended_action="request merge conflict resolution",
                family=family,
                sticky_security=security,
            )
        if family == "jules":
            return _trigger_action(
                pr,
                author_type,
                "jules_conflict",
                f"@google-labs-jules This PR has merge conflicts with `{base}`. Please merge "
                f"the latest `{base}` into this branch, resolve the conflicts, and push.",
                settings,
                now,
                blocker="merge_conflict",
                evidence={"mergeable": mergeable, "mergeStateStatus": merge_state},
                recommended_action="request Jules to resolve merge conflicts",
                family=family,
                sticky_security=security,
            )
        return [
            _escalation(
                pr,
                author_type,
                "merge_conflict",
                evidence={"mergeable": mergeable, "mergeStateStatus": merge_state},
                recommended_action="bounded Stage 2 salvage / conflict repair",
                owner="stage2" if author_type == "BOT" else "human",
                security=security,
            )
        ]

    actions: list[dict[str, Any]] = []
    if merge_state == "BEHIND":
        if family == "dependabot":
            actions.extend(
                _trigger_action(
                    pr,
                    author_type,
                    "dependabot_rebase",
                    "@dependabot rebase",
                    settings,
                    now,
                    blocker="behind_base",
                    evidence={"mergeStateStatus": merge_state},
                    recommended_action="request a bounded rebase",
                    family=family,
                    sticky_security=security,
                )
            )
        elif author_type == "BOT" and not security:
            actions.append(
                {
                    "action": "UPDATE_BRANCH",
                    "repository": repo,
                    "pr": number,
                    "url": pr.get("url"),
                    "head_sha": head,
                    "author_type": author_type,
                    "expected_head_sha": head,
                }
            )
        else:
            actions.append(
                _escalation(
                    pr,
                    author_type,
                    "behind_base",
                    evidence={"mergeStateStatus": merge_state},
                    recommended_action="update the branch from its base or close",
                    security=security,
                )
            )

    if pr.get("checksIncomplete"):
        actions.append(
            {
                "action": "CHECKS_INCOMPLETE",
                "repository": repo,
                "pr": number,
                "url": pr.get("url"),
                "head_sha": head,
                "reason": "status check rollup is truncated or pagination metadata is unavailable",
            }
        )
    else:
        checks = [
            check
            for check in pr.get("checks") or []
            if isinstance(check, dict) and check.get("state") == "FAILURE"
        ]
        advisory_patterns = settings.get("advisory_checks", [])
        if not isinstance(advisory_patterns, list):
            advisory_patterns = []
        codescene = [
            check
            for check in checks
            if str(check.get("name") or "").startswith("CodeScene")
        ]
        if codescene:
            names = sorted({str(check.get("name") or "") for check in codescene})
            actions.extend(
                _trigger_action(
                    pr,
                    author_type,
                    "codescene",
                    "/cs-agent skill:fix-code-health-degradations",
                    settings,
                    now,
                    blocker="codescene_failure",
                    evidence={"checks": names},
                    recommended_action="run the CodeScene code-health remediation",
                    family=family,
                    sticky_security=security,
                )
            )
        required_failures = [
            check
            for check in checks
            if not _advisory(str(check.get("name") or ""), advisory_patterns)
        ]
        if required_failures:
            names = _safe_check_names(
                sorted({str(check.get("name") or "") for check in required_failures})
            )
            if family == "jules":
                actions.extend(
                    _trigger_action(
                        pr,
                        author_type,
                        "jules_checks",
                        f"@google-labs-jules These checks are failing on this PR: {', '.join(names)}. "
                        "Please fix the failures and push to this branch.",
                        settings,
                        now,
                        blocker="required_check_failure",
                        evidence={"checks": names},
                        recommended_action="request Jules to fix failing required checks",
                        family=family,
                        sticky_security=security,
                    )
                )
            elif family == "coderabbit" and author_type == "BOT":
                actions.extend(
                    _trigger_action(
                        pr,
                        author_type,
                        "coderabbit_fixci",
                        "@coderabbitai fix-ci commit",
                        settings,
                        now,
                        blocker="required_check_failure",
                        evidence={"checks": names},
                        recommended_action="request CodeRabbit to fix failing CI",
                        family=family,
                        sticky_security=security,
                    )
                )
            else:
                actions.append(
                    _escalation(
                        pr,
                        author_type,
                        "required_check_failure",
                        evidence={"checks": names},
                        recommended_action="fix failing checks or close",
                        owner="human",
                        security=security,
                    )
                )
        advisory_failures = [
            check
            for check in checks
            if _advisory(str(check.get("name") or ""), advisory_patterns)
        ]
        if advisory_failures:
            names = sorted(
                {str(check.get("name") or "") for check in advisory_failures}
            )
            actions.append(
                {
                    "action": "ADVISORY_ONLY",
                    "repository": repo,
                    "pr": number,
                    "url": pr.get("url"),
                    "checks": names,
                    "reason": "Stage 1 routine predicates may treat advisory checks as green.",
                }
            )

    if str(pr.get("reviewDecision") or "").upper() == "CHANGES_REQUESTED":
        coderabbit_review = any(
            isinstance(review, dict)
            and str(review.get("state") or "").upper() == "CHANGES_REQUESTED"
            and str((review.get("author") or {}).get("login") or "").lower()
            == "coderabbitai[bot]"
            for review in pr.get("latestReviews") or []
        )
        if coderabbit_review and author_type == "BOT":
            actions.extend(
                _trigger_action(
                    pr,
                    author_type,
                    "coderabbit_autofix",
                    "@coderabbitai autofix",
                    settings,
                    now,
                    blocker="changes_requested",
                    evidence={"reviewDecision": "CHANGES_REQUESTED"},
                    recommended_action="request CodeRabbit autofix",
                    family=family,
                    sticky_security=security,
                )
            )
        elif family == "jules":
            actions.extend(
                _trigger_action(
                    pr,
                    author_type,
                    "jules_review",
                    "@google-labs-jules Please address the requested changes in the latest review "
                    "on this PR and push.",
                    settings,
                    now,
                    blocker="changes_requested",
                    evidence={"reviewDecision": "CHANGES_REQUESTED"},
                    recommended_action="request Jules to address review changes",
                    family=family,
                    sticky_security=security,
                )
            )
        else:
            actions.append(
                _escalation(
                    pr,
                    author_type,
                    "changes_requested",
                    evidence={"reviewDecision": "CHANGES_REQUESTED"},
                    recommended_action="address requested review changes or close",
                    security=security,
                )
            )
    return actions


def _run_github_step(
    argv: list[str], step: str, *, run: Any = subprocess.run
) -> dict[str, Any]:
    try:
        result = run(
            argv,
            check=False,
            capture_output=True,
            text=True,
            timeout=60,
        )
    except (OSError, subprocess.SubprocessError) as exc:
        return {"step": step, "exit_code": None, "error": type(exc).__name__}
    return {"step": step, "exit_code": result.returncode}


def _apply_action(action: dict[str, Any], *, run: Any = subprocess.run) -> None:
    repo = str(action["repository"])
    pr = str(action["pr"])
    steps: list[dict[str, Any]] = []
    if action["action"] == "UPDATE_BRANCH":
        steps.append(
            _run_github_step(
                [
                    "gh",
                    "api",
                    "-X",
                    "PUT",
                    f"repos/{repo}/pulls/{pr}/update-branch",
                    "-f",
                    f"expected_head_sha={action['expected_head_sha']}",
                ],
                "update_branch",
                run=run,
            )
        )
    elif action["action"] == "TRIGGER":
        steps.append(
            _run_github_step(
                [
                    "gh",
                    "pr",
                    "comment",
                    pr,
                    "--repo",
                    repo,
                    "--body",
                    str(action["body"]),
                ],
                "trigger_comment",
                run=run,
            )
        )
    else:
        steps.append(
            _run_github_step(
                [
                    "gh",
                    "pr",
                    "comment",
                    pr,
                    "--repo",
                    repo,
                    "--body",
                    str(action["comment"]),
                ],
                "comment",
                run=run,
            )
        )
        steps.append(
            _run_github_step(
                [
                    "gh",
                    "label",
                    "create",
                    "superseded",
                    "--repo",
                    repo,
                    "--color",
                    "cfd3d7",
                    "--description",
                    "Superseded by another PR (pr-lifecycle)",
                ],
                "ensure_label",
                run=run,
            )
        )
        steps.append(
            _run_github_step(
                [
                    "gh",
                    "pr",
                    "edit",
                    pr,
                    "--repo",
                    repo,
                    "--add-label",
                    "superseded",
                ],
                "label",
                run=run,
            )
        )
        steps.append(
            _run_github_step(
                ["gh", "pr", "close", pr, "--repo", repo],
                "close",
                run=run,
            )
        )
        try:
            result = run(
                [
                    "gh",
                    "pr",
                    "view",
                    pr,
                    "--repo",
                    repo,
                    "--json",
                    "state",
                ],
                check=False,
                capture_output=True,
                text=True,
                timeout=60,
            )
            read = {"step": "confirm", "exit_code": result.returncode}
        except (OSError, subprocess.SubprocessError) as exc:
            result = None
            read = {
                "step": "confirm",
                "exit_code": None,
                "error": type(exc).__name__,
            }
        if read["exit_code"] == 0:
            try:
                payload = json.loads(result.stdout)
                read["state"] = payload.get("state")
            except (json.JSONDecodeError, AttributeError):
                read["state"] = None
        steps.append(read)
    action["github_steps"] = steps
    action["unconfirmed"] = any(
        step.get("exit_code") != 0
        for step in steps
        if step.get("step") != "ensure_label"
    )
    if action["action"] in {"CLOSE_STALE_LINEAGE", "CLOSE_SUPERSEDED"}:
        confirm = next((step for step in steps if step["step"] == "confirm"), {})
        if str(confirm.get("state") or "").upper() != "CLOSED":
            action["unconfirmed"] = True


def _human_ledger_rows(
    repo: str, ledger: dict[str, Any], packet_expiry_days: int
) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    for item in ledger.get("items") or []:
        if (
            not isinstance(item, dict)
            or item.get("repository") != repo
            or item.get("lifecycle_state") == "TERMINAL"
            or (
                item.get("current_owner") != "human"
                and item.get("guardrail_outcome") != "REVIEW_SECURITY"
            )
        ):
            continue
        next_action = str(item.get("next_action") or "")
        expires_match = _EXPIRES_RE.search(next_action)
        expires = expires_match.group(1) if expires_match else None
        if expires is None:
            updated = _parse_datetime(item.get("updated_at_utc"))
            if updated is not None:
                expires = _iso(updated + timedelta(days=packet_expiry_days))
        rows.append(
            {
                "repository": repo,
                "pr": item.get("pr"),
                "url": item.get("url"),
                "blocker": item.get("guardrail_outcome") or "human_decision",
                "evidence": next_action[:200],
                "recommended_action": next_action[:200],
                "safe_default": item.get("safe_default")
                or "Leave open; no merge or close without a human decision.",
                "owner": "human",
                "expires": expires,
                "packet_expiry_close_days": packet_expiry_days,
            }
        )
    return rows


def _rows_for_repo(
    repo: str,
    actions: list[dict[str, Any]],
    ledger: dict[str, Any],
    packet_expiry_days: int,
) -> list[dict[str, Any]]:
    rows = _human_ledger_rows(repo, ledger, packet_expiry_days)
    rows.extend(
        {
            **action,
            "packet_expiry_close_days": packet_expiry_days,
        }
        for action in actions
        if action.get("action") == "ESCALATE" and action.get("repository") == repo
    )
    return rows


def _repo_counts(
    actions: list[dict[str, Any]], repositories: list[str]
) -> dict[str, Any]:
    result: dict[str, Any] = {}
    for repo in repositories:
        repo_actions = [
            action for action in actions if action.get("repository") == repo
        ]
        result[repo] = {
            "by_action": dict(
                Counter(action.get("action", "UNKNOWN") for action in repo_actions)
            ),
            "by_blocker": dict(
                Counter(
                    str(action.get("blocker"))
                    for action in repo_actions
                    if action.get("blocker")
                )
            ),
        }
    return result


def _load_full_comments(pr: dict[str, Any], *, run: Any) -> None:
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
    repository = pr.get("repository")
    number = pr.get("number")
    if (
        not isinstance(repository, str)
        or not repository
        or not isinstance(number, int)
        or isinstance(number, bool)
        or number < 1
    ):
        pr["comments_incomplete"] = True
        return
    try:
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
        payload = json.loads(result.stdout)
        if not isinstance(payload, list):
            raise TypeError("malformed comments payload")
        if all(isinstance(page, list) for page in payload):
            raw_comments = [comment for page in payload for comment in page]
        elif all(isinstance(comment, dict) for comment in payload):
            raw_comments = payload
        else:
            raise ValueError("malformed comments payload")
        if not all(isinstance(comment, dict) for comment in raw_comments):
            raise ValueError("malformed comments payload")
        if len(raw_comments) < total_count:
            raise ValueError("incomplete comments payload")
        normalized: list[dict[str, Any]] = []
        for comment in raw_comments:
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
            normalized.append(
                {
                    "author": {"login": author.get("login") or ""},
                    "body": body or "",
                    "createdAt": created_at,
                }
            )
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


def run_unblock(
    *,
    apply: bool,
    json_out: bool,
    repos_filter: list[str] | None,
    limit: int | None,
    run: Any = subprocess.run,
) -> int:
    config = load_yaml(ROOT / "tasks/pr-review-agent.config.yaml")
    validate_config(config)
    repositories = list(config["repos"])
    if repos_filter:
        unknown = sorted(set(repos_filter) - set(repositories))
        if unknown:
            raise ValueError(f"unknown repository filter: {', '.join(unknown)}")
        repositories = [repo for repo in repositories if repo in set(repos_filter)]
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
            for pr in prs:
                comments = pr.get("comments")
                comment_count = len(comments) if isinstance(comments, list) else 0
                total_count = pr.get("commentsTotalCount")
                if (
                    isinstance(total_count, int)
                    and not isinstance(total_count, bool)
                    and total_count > comment_count
                ):
                    comment_history_fetch_pr_count += 1
                _load_full_comments(pr, run=run)
                verdict = classify_pr_identity(pr, policy)
                matching = [
                    item
                    for item in ledger.get("items") or []
                    if isinstance(item, dict)
                    and item.get("repository") == repo
                    and item.get("pr") == pr.get("number")
                ]
                actions.extend(
                    route_pr(
                        pr,
                        author_type=verdict.author_type,
                        ledger_items_for_pr=matching,
                        ledger=ledger,
                        settings=settings,
                        now=datetime.now(timezone.utc),
                    )
                )
        actions.extend(inventory_failed)
        deferred_by_cap: list[dict[str, Any]] = []
        mutation_count = 0
        for action in actions:
            if action.get("action") not in _MUTATING_ACTIONS:
                continue
            if mutation_count >= cap:
                deferred_by_cap.append(action)
                continue
            mutation_count += 1
            if apply:
                _apply_action(action)

        now = datetime.now(timezone.utc)
        packet_expiry_days = lifecycle.get("packet_expiry_close_days", 7)
        if not isinstance(packet_expiry_days, int) or packet_expiry_days < 1:
            packet_expiry_days = 7
        escalation_issues: dict[str, Any] = {}
        failed_repos = {
            entry["repository"] for entry in inventory_failed if entry.get("repository")
        }
        for repo in repositories:
            if repo in failed_repos:
                escalation_issues[repo] = {
                    "action": "ISSUE_UPDATE_SKIPPED",
                    "repository": repo,
                    "reason": "INVENTORY_FAILED",
                }
                continue
            rows = _rows_for_repo(repo, actions, ledger, packet_expiry_days)
            if apply:
                try:
                    escalation_issues[repo] = update_backlog_issue(repo, rows, now=now)
                except (OSError, subprocess.SubprocessError) as exc:
                    escalation_issues[repo] = {
                        "action": "ISSUE_UPDATE_FAILED",
                        "repository": repo,
                        "reason": type(exc).__name__,
                    }
            else:
                escalation_issues[repo] = {
                    "row_count": len(rows),
                    "body": backlog_issue_body(repo, rows, {}, now),
                }
        plan = {
            "dry_run": not apply,
            "ledger_revision": ledger.get("ledger_revision"),
            "repositories": _repo_counts(actions, repositories),
            "action_count": len(actions),
            "actions": actions,
            "deferred_by_cap": deferred_by_cap,
            "deferred_by_cap_count": len(deferred_by_cap),
            "mutation_cap": cap,
            "mutations_selected": mutation_count,
            "mutations_applied": mutation_count if apply else 0,
            "inventory_failed": inventory_failed,
            "comment_history_fetch_pr_count": comment_history_fetch_pr_count,
            "escalation_issues": escalation_issues,
        }
        _emit(plan, json_out)
    return 0


def _emit(plan: dict[str, Any], json_out: bool) -> None:
    if json_out:
        print(json.dumps(plan, indent=2, sort_keys=True))
        return
    print(
        f"PR lifecycle unblock: {plan['action_count']} actions across "
        f"{len(plan['repositories'])} repositories; "
        f"{plan['deferred_by_cap_count']} deferred by cap"
    )


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--apply", action="store_true")
    parser.add_argument("--json", action="store_true", dest="json_out")
    parser.add_argument("--repo", action="append", dest="repos_filter")
    parser.add_argument("--limit", type=int)
    return parser


def main(argv: list[str] | None = None) -> int:
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
