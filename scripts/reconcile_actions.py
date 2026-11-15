"""Action classification and execution for PR lifecycle reconciliation."""

from __future__ import annotations

from datetime import datetime
from typing import Any

import pr_lifecycle_reconcile_guards as guards
from pr_identity import classify_pr_identity
from pr_lifecycle_config import normalize_exclusions
from pr_lifecycle_support import ROOT

from .reconcile_github import _gh_pr_diff, _gh_pr_files, _gh_pr_view


_CLOSED_LABEL_DISPOSITIONS = {
    "duplicate": "CLOSED_DUPLICATE",
    "superseded": "CLOSED_SUPERSEDED",
    "stale-auto-closed": "CLOSED_STALE",
    "wontfix": "HUMAN_REJECTED",
    "declined": "HUMAN_REJECTED",
}


def _label_names(live: dict[str, Any]) -> list[str]:
    """Sorted label names from a live PR payload."""
    return sorted(
        label["name"]
        for label in live.get("labels") or []
        if isinstance(label, dict) and isinstance(label.get("name"), str)
    )


def _classify_live_merge(
    item: dict[str, Any], live: dict[str, Any], key: str
) -> dict[str, Any] | None:
    merger = str((live.get("mergedBy") or {}).get("login") or "")
    if not merger:
        return _pending_terminal(item, key, "MERGED", "mergedBy unavailable")
    completion_owned = (
        item.get("lifecycle_state") == "STAGE3_RECONCILIATION"
        or item.get("current_owner") == "stage3"
    )
    disposition = "MERGED_BOUNDED_COMPLETION" if completion_owned else "MERGED_ROUTINE"
    return {
        "action": "TERMINAL_MERGED",
        "key": key,
        "to_state": "TERMINAL",
        "disposition": disposition,
        "reason": f"live PR state=MERGED mergedBy={merger}",
        "evidence": {"mergedBy": merger},
    }


def _classify_live_close(
    item: dict[str, Any], live: dict[str, Any], key: str
) -> dict[str, Any] | None:
    """Classify a closed PR by its labels.

    Without a disposition label: a REVIEW_SECURITY item closed unmerged was
    never security-reviewed, so it terminates CLOSED_UNREVIEWED; anything
    else terminates CLOSED_NOOP. (Pending classification remains merge-only:
    a MERGED live state without merger evidence still routes to Stage 3.)
    """
    labels = _label_names(live)
    disposition = next(
        (
            _CLOSED_LABEL_DISPOSITIONS[name]
            for name in labels
            if name in _CLOSED_LABEL_DISPOSITIONS
        ),
        None,
    )
    if disposition is None:
        if item.get("guardrail_outcome") == "REVIEW_SECURITY":
            return {
                "action": "TERMINAL_CLOSED",
                "key": key,
                "to_state": "TERMINAL",
                "disposition": "CLOSED_UNREVIEWED",
                "reason": (
                    "live PR state=CLOSED unmerged under REVIEW_SECURITY "
                    "without disposition label; closed before review "
                    "→ CLOSED_UNREVIEWED"
                ),
                "evidence": {"labels": labels},
            }
        return {
            "action": "TERMINAL_CLOSED",
            "key": key,
            "to_state": "TERMINAL",
            "disposition": "CLOSED_NOOP",
            "reason": (
                "live PR state=CLOSED without disposition label; "
                "closed outside lifecycle → CLOSED_NOOP"
            ),
            "evidence": {"labels": labels},
        }
    return {
        "action": "TERMINAL_CLOSED",
        "key": key,
        "to_state": "TERMINAL",
        "disposition": disposition,
        "reason": f"live PR state=CLOSED labels={labels}",
        "evidence": {"labels": labels},
    }


def _pending_terminal(
    item: dict[str, Any], key: str, observed: str, detail: str
) -> dict[str, Any] | None:
    """Route an unclassified merge to Stage 3 when merger evidence is absent.

    Non-Stage-3 items route to Stage 3 for classification; an item already
    Stage-3-owned gets an in-place observation note (same-state handoffs are
    illegal). A prior identical observation is not re-emitted.
    """
    marker = f"Observed {observed} unclassified"
    if marker in str(item.get("next_action") or ""):
        return None
    if item.get("lifecycle_state") != "STAGE3_RECONCILIATION":
        return {
            "action": "TERMINAL_PENDING",
            "key": key,
            "to_state": "STAGE3_RECONCILIATION",
            "disposition": None,
            "observed_state": observed,
            "reason": (
                f"live state={observed} without classifying evidence "
                f"({detail}); route to Stage 3"
            ),
            "evidence": {"observed_state": observed, "detail": detail},
        }
    return {
        "action": "TERMINAL_OBSERVED",
        "key": key,
        "observed_state": observed,
        "reason": f"{marker}: {detail}",
        "evidence": {"observed_state": observed, "detail": detail},
    }


def _classify_live_terminal(
    item: dict[str, Any], live: dict[str, Any], key: str
) -> dict[str, Any] | None:
    """Return a terminal or pending action for a merged/closed live PR."""
    live_state = str(live.get("state") or "").upper()
    if live_state == "MERGED":
        return _classify_live_merge(item, live, key)
    if live_state == "CLOSED":
        # A closed PR with a mergedAt timestamp was merged, not abandoned —
        # mergedAt is the authoritative signal, not the state label.
        if live.get("mergedAt"):
            return _classify_live_merge(item, live, key)
        return _classify_live_close(item, live, key)
    return None


def _field_drift(ledger_val: object, live_val: object) -> bool:
    ledger = str(ledger_val or "")
    live = str(live_val or "")
    return bool(live and ledger and live.lower() != ledger.lower())


def _drift_fields(item: dict[str, Any], live: dict[str, Any]) -> tuple[str, str, bool]:
    live_head = str(live.get("headRefOid") or "")
    live_base = str(live.get("baseRefOid") or "")
    drifted = _field_drift(item.get("head_sha"), live_head) or _field_drift(
        item.get("base_sha"), live_base
    )
    return live_head, live_base, drifted


def _classify_sha_drift(
    item: dict[str, Any], live: dict[str, Any], key: str
) -> dict[str, Any] | None:
    live_head, live_base, drifted = _drift_fields(item, live)
    if not drifted:
        return None
    if item.get("lifecycle_state") == "STAGE1_INTAKE":
        # Same-state handoffs are not legal transitions; re-anchor in place.
        return {
            "action": "REANCHOR_HEAD",
            "key": key,
            "reason": f"re-anchor intake to live head {live_head[:12]}",
            "live_head_sha": live_head,
            "live_base_sha": live_base,
        }
    ledger_head = str(item.get("head_sha") or "")
    return {
        "action": "SHA_DRIFT_REINTAKE",
        "key": key,
        "to_state": "STAGE1_INTAKE",
        "disposition": None,
        "reason": f"head/base drift ledger={ledger_head[:12]} live={live_head[:12]}",
        "live_head_sha": live_head,
        "live_base_sha": live_base,
    }


def _item_age_days(item: dict[str, Any], now: datetime) -> float | None:
    """Return days since the item update, or None for an invalid timestamp."""
    from .reconcile_main import _parse_utc
    stamp = _parse_utc(item.get("updated_at_utc"))
    if stamp is None:
        return None
    return (now - stamp).total_seconds() / 86400.0


def _classify_stale(
    item: dict[str, Any],
    *,
    key: str,
    policy: Any,
) -> dict[str, Any] | None:
    """Return a stale-close action for an expired eligible bot packet."""
    stale_candidate = (
        item.get("lifecycle_state") == "WAITING_HUMAN"
        and item.get("author_type") == "BOT"
        and item.get("guardrail_outcome") != "REVIEW_SECURITY"
    )
    if not stale_candidate:
        return None
    if guards.stale_close_hold_reason(item, policy.exclusions) is not None:
        return None
    age = _item_age_days(item, policy.now)
    if age is None or age <= policy.expiry_days:
        return None
    age_label = str(round(age, 1))
    return {
        "action": "CLOSE_STALE",
        "key": key,
        "to_state": "TERMINAL",
        "disposition": "CLOSED_STALE",
        "reason": (
            f"WAITING_HUMAN BOT non-REVIEW_SECURITY age={age_label}d "
            f"> {policy.expiry_days}d"
        ),
        "repository": item.get("repository"),
        "pr": item.get("pr"),
        "head_sha": item.get("head_sha"),
    }


def _needs_path_backfill(item: dict[str, Any]) -> bool:
    """True for a nonterminal item whose changed-path evidence is absent."""
    paths = item.get("changed_paths")
    return item.get("lifecycle_state") != "TERMINAL" and not (
        isinstance(paths, list) and paths
    )


def _backfill_eligible(item: dict[str, Any], live: Any) -> bool:
    """True only when a pathless nonterminal item faces an open live PR."""
    return (
        _needs_path_backfill(item)
        and isinstance(live, dict)
        and str(live.get("state") or "").upper() == "OPEN"
        and bool(str(item.get("repository") or ""))
        and _positive_pr_number(item.get("pr"))
    )


def _is_live_open(live: dict[str, Any] | None) -> bool:
    """Check if the live PR is open."""
    return isinstance(live, dict) and str(live.get("state") or "").upper() == "OPEN"


def _is_bot_author(item: dict[str, Any]) -> bool:
    """Check if the item is authored by a bot."""
    return item.get("author_type") == "BOT"


def _is_security_classification(item: dict[str, Any]) -> bool:
    """Check if the item is classified as SECURITY."""
    return item.get("classification") == "SECURITY"


def _has_security_backing(item: dict[str, Any]) -> bool:
    """Check if the item has security backing."""
    paths = item.get("changed_paths")
    return isinstance(paths, list) and paths and guards.has_path_security_backing(paths)


def _should_reconcile_security_tag(
    item: dict[str, Any], live: dict[str, Any] | None
) -> bool:
    """Check if the item should be reconciled for security tag."""
    if not _is_live_open(live):
        return False
    if item.get("lifecycle_state") == "TERMINAL":
        return False
    if not _is_bot_author(item):
        return False
    if not _is_security_classification(item):
        return False
    if guards.is_forced_security_hold(guards.sentinel_record(item, live)):
        return False
    if _drift_fields(item, live)[2]:
        return False
    return not _has_security_backing(item)


def _fetch_diff_from_item(item: dict[str, Any]) -> str | None:
    """Fetch diff text from the item."""
    diff_text = item.get("diff_text")
    return str(diff_text).strip() if diff_text else None


def _fetch_diff_from_live(live: dict[str, Any]) -> str | None:
    """Fetch diff text from the live PR."""
    diff_text = live.get("diff_text")
    return str(diff_text).strip() if diff_text else None


def _fetch_diff_from_gh_cli(item: dict[str, Any]) -> str | None:
    """Fetch diff text from the GitHub CLI."""
    repo = str(item.get("repository") or "")
    pr_num = item.get("pr")
    if not repo or not _positive_pr_number(pr_num):
        return None
    return _gh_pr_diff(repo, int(pr_num))


def _fetch_diff_text(
    item: dict[str, Any], live: dict[str, Any] | None
) -> str | None:
    """Fetch the diff text for the item, preferring item, then live, then gh CLI."""
    diff_text = _fetch_diff_from_item(item)
    if diff_text is None and live:
        diff_text = _fetch_diff_from_live(live)
    if diff_text is None:
        diff_text = _fetch_diff_from_gh_cli(item)
    return diff_text if diff_text and diff_text.strip() else None


def _security_tag_reconcile_action(
    item: dict[str, Any], live: dict[str, Any] | None
) -> dict[str, Any] | None:
    """Plan reclassification for an open, nonterminal BOT PR lacking backing.

    Return None for forced holds, head/base drift, missing changed paths,
    security backing, or a failed or empty diff lookup. Prefer the item's diff, then the live PR's diff,
    fetching via gh only when both are None. Do not mutate the item or PR.
    """
    if not _should_reconcile_security_tag(item, live):
        return None
    diff_text = _fetch_diff_text(item, live)
    if diff_text is None:
        return None
    return guards.evaluate_security_tag_reconcile(item, diff_text=diff_text)


def _path_backfill_action(
    item: dict[str, Any], live: dict[str, Any] | None
) -> dict[str, Any] | None:
    """Emit a changed_paths backfill for an open live PR missing path evidence."""
    # Data-only action: it stamps `changed_paths` so the guardrail evaluator
    # can judge the item on real evidence instead of holding it forever on a
    # missing list. Fetch failures emit PATH_BACKFILL_FAILED for visibility
    # (never applied); non-OPEN live states skip the fetch entirely.
    if not _backfill_eligible(item, live):
        return None
    repo = str(item["repository"])
    pr_num = int(item["pr"])
    key = str(item.get("key") or "")
    paths = _gh_pr_files(repo, pr_num)
    if paths is None:
        return {
            "action": "PATH_BACKFILL_FAILED",
            "key": key,
            "repository": repo,
            "pr": pr_num,
            "reason": "changed-paths fetch failed; item stays unevaluated",
        }
    return {
        "action": "BACKFILL_PATHS",
        "key": key,
        "repository": repo,
        "pr": pr_num,
        "paths": paths,
        "reason": f"backfill changed_paths ({len(paths)} files) for guardrail evidence",
    }


def _handle_backfill_action(
    item: dict[str, Any], live: dict[str, Any] | None
) -> dict[str, Any] | None:
    """Handle the backfill action for changed paths."""
    return _path_backfill_action(item, live)


def _handle_reclassify_action(
    item: dict[str, Any], live: dict[str, Any] | None
) -> dict[str, Any] | None:
    """Handle the reclassify action for security tags."""
    return _security_tag_reconcile_action(item, live)


def _sentinel_hold_action(
    item: dict[str, Any], live: dict[str, Any] | None
) -> dict[str, Any] | None:
    """Plan a fixed REVIEW_SECURITY hold for an open Sentinel persona or branch."""
    if not _sentinel_hold_eligible(item, live):
        return None
    return {
        "action": "HOLD_SENTINEL_SECURITY",
        "key": str(item.get("key") or ""),
        "repository": str(item.get("repository") or ""),
        "pr": item.get("pr"),
        "reason": (
            "Jules Sentinel persona or sentinel/ branch is a fixed "
            "REVIEW_SECURITY hold; title-only reconcile cannot clear it"
        ),
    }


def _sentinel_hold_eligible(item: dict[str, Any], live: dict[str, Any] | None) -> bool:
    """Return whether this open BOT item may receive a Sentinel hold."""
    if item.get("lifecycle_state") == "TERMINAL":
        return False
    if item.get("author_type") != "BOT":
        return False
    if item.get("guardrail_outcome") not in {None, "NOT_RUN", "PASS_ROUTINE", "REVIEW_SECURITY"}:
        return False
    if not isinstance(live, dict):
        return False
    if str(live.get("state") or "").upper() != "OPEN":
        return False
    if not guards.is_sentinel_security_pr(guards.sentinel_record(item, live)):
        return False
    return not _sentinel_already_held(item)


def _sentinel_already_held(item: dict[str, Any]) -> bool:
    """Return whether a Sentinel item is already a fixed REVIEW_SECURITY hold."""
    if item.get("guardrail_outcome") != "REVIEW_SECURITY":
        return False
    next_action = str(item.get("next_action") or "")
    return (
        guards.SENTINEL_HOLD_MARKER in next_action
        or item.get("guardrail_source") in {"review", "human", "octopus"}
        or item.get("current_owner") in {"human", "stage2", "stage3"}
        or item.get("risk_class") == "HUMAN_REVIEW"
    )


def _handle_sentinel_hold_action(
    item: dict[str, Any], live: dict[str, Any] | None
) -> dict[str, Any] | None:
    """Handle the sentinel hold action."""
    return _sentinel_hold_action(item, live)


def _positive_pr_number(value: Any) -> bool:
    """Require a positive int PR number (bool excluded)."""
    return isinstance(value, int) and not isinstance(value, bool) and value >= 1


def classify_item(
    item: dict[str, Any],
    live: dict[str, Any] | None,
    *,
    policy: Any,
) -> dict[str, Any] | None:
    """Return a proposed action, or None when no change is needed."""
    if item.get("lifecycle_state") == "TERMINAL":
        return None
    key = str(item.get("key") or "")
    if live is None:
        return {
            "action": "LIVE_LOOKUP_FAILED",
            "key": key,
            "reason": "gh pr view failed; skip mutation",
        }
    # A merged or closed PR is done. An already-noted observation returns None;
    # do not fall through into SHA re-intake just because the recorded head
    # differs from the closed head.
    live_state = str(live.get("state") or "").upper()
    if live_state in {"MERGED", "CLOSED"}:
        return _classify_live_terminal(item, live, key)
    return _classify_sha_drift(item, live, key) or _classify_stale(
        item, key=key, policy=policy
    )


def _action_for_item(
    item: Any,
    policy: Any,
) -> list[dict[str, Any]]:
    """Look up and classify one nonterminal item; return planned actions."""
    # Data-only actions (path backfill and title-only security tag clearing)
    # ride alongside the primary action so guardrails evaluate real evidence.
    if not isinstance(item, dict):
        return []
    if item.get("lifecycle_state") == "TERMINAL":
        return []
    repo = str(item.get("repository") or "")
    pr = item.get("pr")
    live = _gh_pr_view(repo, int(pr)) if repo and pr else None
    primary = classify_item(item, live, policy=policy)
    actions = [primary] if primary is not None else []

    backfill = _handle_backfill_action(item, live)
    if backfill is not None:
        actions.append(backfill)

    reclassify = _handle_reclassify_action(item, live)
    if reclassify is not None:
        actions.append(reclassify)

    sentinel_hold = _handle_sentinel_hold_action(item, live)
    if sentinel_hold is not None:
        # SECURITY: do not stale-close a PR this pass is about to hold.
        actions = [
            action for action in actions if action.get("action") != "CLOSE_STALE"
        ]
        actions.append(sentinel_hold)

    return actions