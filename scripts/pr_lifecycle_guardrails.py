"""Deterministic guardrail evaluation for lifecycle ledger items.

Classify each nonterminal item's ``changed_paths`` into the
``sensitive_path_taxonomy`` classes from ``tasks/pr-review-agent.config.yaml``,
then write ``sensitive_paths``, ``guardrail_outcome``, and ``risk_class``.

This replaces the Stage 1 stand-in that bulk-marked 127+ items
``REVIEW_SECURITY`` without evaluating paths: items whose paths hit a sticky
class keep ``REVIEW_SECURITY``; paths hitting only ``generated_output`` or no
class become ``PASS_ROUTINE``. ``HOLD_*`` outcomes, ``CLOSE_NONSECURITY_NOOP``,
``ANALYSIS_ERROR``, and ``TERMINAL`` items are never touched — they encode
non-path holds a path classifier cannot clear.

Dry-run by default; ``--apply`` CAS-commits through ``pr_lifecycle_ledger_cas``.
The path rules are heuristic v1 (revision 2026-08-19 taxonomy): a missed
pattern is a policy-revision question, not a code bug — extend ``_PATH_RULES``
rather than special-casing items.
"""

from __future__ import annotations

import argparse
import json
import re
import sys
import tempfile
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import pr_lifecycle_ledger_cas as cas
from pr_lifecycle_persist import dump_ledger
from pr_lifecycle_yaml import load_yaml

ROOT = Path(__file__).resolve().parents[1]
CONFIG_PATH = ROOT / "tasks/pr-review-agent.config.yaml"

_COMMIT_MESSAGE = "chore(lifecycle): deterministic guardrail path evaluation"
_EVALUATABLE = {"NOT_RUN", "REVIEW_SECURITY", None}
_STICKY_EXEMPT = {"generated_output"}
# Owners whose holds must never be rewritten by an unattended evaluator,
# matching the unblock router's blocked-owner set.
_BLOCKED_OWNERS = {"human", "stage2", "stage3"}
# guardrail_source values that mark a hold/outcome recorded by a real review
# (a human or a security reviewer) rather than path evidence. Even
# --clear-stand-in never downgrades these.
_PROTECTED_SOURCES = {"manual", "review", "human", "octopus"}
# Identity classifications the intake classifier marked as security work.
# These stay held regardless of path evidence — a Sentinel fix can touch
# only ordinary source files yet still be a security change.
_SECURITY_CLASSIFICATIONS = {"SECURITY"}

# (taxonomy class, regex matched against each changed path). Patterns are
# anchored per path segment; order matters only for readability.
_PATH_RULES: tuple[tuple[str, str], ...] = (
    (
        "workflows_and_permissions",
        r"(^|/)\.github/(workflows|actions|rulesets|scripts|hooks|agents|commands|copilot|jules|CODEOWNERS|github-app\.ya?ml|repository-automation\.ya?ml|dependabot\.ya?ml|pull_request_template)|(^|/)(\.claude/|\.agents/|\.windsurf/|\.codeium/|\.mcp\.json$|AGENTS\.md$|CLAUDE\.md$|\.cursorrules$|docs/cursor-automations/(prompts|exports)/)",
    ),
    (
        "secrets",
        r"(^|/)(\.env($|\.)|[^/]*\.env$|secrets?/|credentials?[^/]*|[^/]*\.(pem|key|p12|pfx|keystore)$|id_(rsa|ed25519|ecdsa|dsa)|\.ssh/|[^/]*netrc)",
    ),
    (
        "authentication_and_authorization",
        r"[^/]*(authentication|authorization|oauth|rbac|permission|sso|login)[^/]*\.(py|sh|js|ts|ya?ml|json|toml|rb|go|fish)$",
    ),
    (
        "deployment_and_infrastructure",
        r"(^|/)(Dockerfile[^/]*|docker-compose[^/]*|\.devcontainer/|deploy[^/]*/|infrastructure/|terraform[^/]*|[^/]*\.tf$|fly\.toml|vercel\.json|launchd[^/]*|launch-agents/|[^/]*\.plist$|systemd[^/]*|[^/]*\.service$)",
    ),
    (
        "lockfiles_and_major_dependencies",
        r"(^|/)(package-lock\.json|yarn\.lock|pnpm-lock\.ya?ml|uv\.lock|poetry\.lock|Pipfile\.lock|Gemfile\.lock|go\.(mod|sum)|Cargo\.(toml|lock)|composer\.(json|lock)|requirements[^/]*\.txt|requirements/|pyproject\.toml|setup\.(py|cfg)|package\.json|Brewfile[^/]*|[^/]*\.gemspec|renv\.lock)",
    ),
    (
        "security_configuration",
        r"(^|/)(\.trunk/|\.github/gitleaks\.toml|[^/]*gitleaks[^/]*|[^/]*codeql[^/]*|[^/]*semgrep[^/]*|[^/]*trufflehog[^/]*|[^/]*trivy[^/]*|[^/]*snyk[^/]*|\.codacy\.ya?ml|[^/]*sonar[^/]*\.(ya?ml|properties)|[^/]*zizmor[^/]*|SECURITY\.md|\.github/SECURITY[^/]*)",
    ),
    (
        "database_migrations",
        r"(^|/)(migrations?/|alembic[^/]*|[^/]*\.sql$|schema\.prisma|prisma/migrations)",
    ),
    (
        "network_and_browser_origins",
        r"[^/]*(dns|network|cors|proxy|origin)[^/]*\.(ya?ml|toml|json|conf|cfg|sh|py|js|ts|fish)$|(^|/)(hosts|resolv\.conf|pf\.conf|ctrld[^/]*\.toml|nginx[^/]*|[^/]*\.zone$)",
    ),
    (
        "shell_execution",
        r"[^/]*\.(sh|bash|zsh|fish|command|bat|ps1)$|(^|/)(Makefile|[^/]*\.mk$|bin/)",
    ),
    (
        "file_read_write_boundaries",
        r"(^|/)(\.gitignore|\.gitattributes|\.cursorignore|[^/]*ignore$|\.cursor/|\.devin/|\.idea/|\.vscode/)",
    ),
    (
        "generated_output",
        r"(^|/)(\.jules/|jules/|generated/|dist/|build/|coverage/|\.snapshot[^/]*|[^/]*\.generated\.[^/]*$)",
    ),
    (
        "public_api_contracts",
        r"(^|/)(openapi[^/]*|swagger[^/]*|schemas?/|apis?/|api[^/]*\.(json|ya?ml)|[^/]*\.proto$|[^/]*\.graphql|[^/]*\.schema\.json)",
    ),
    (
        "destructive_data_actions",
        r"[^/]*(delete|purge|wipe|destroy|truncate|drop|erase)[^/]*\.(sh|py|sql|js|ts|rb|fish)$",
    ),
)
_COMPILED_RULES: tuple[tuple[str, re.Pattern[str]], ...] = tuple(
    (name, re.compile(pattern, re.IGNORECASE)) for name, pattern in _PATH_RULES
)


def classify_path(path: Any) -> set[str]:
    """Return the taxonomy classes a changed path matches (empty when clean)."""
    if not isinstance(path, str) or not path.strip():
        return set()
    return {name for name, pattern in _COMPILED_RULES if pattern.search(path.strip())}


def classify_item_paths(changed_paths: Any) -> set[str]:
    """Union the taxonomy classes across one item's changed paths."""
    if not isinstance(changed_paths, list):
        return set()
    classes: set[str] = set()
    for path in changed_paths:
        classes.update(classify_path(path))
    return classes


def _evaluable(item: dict[str, Any]) -> bool:
    """True for a nonterminal BOT item eligible for path re-evaluation.

    Non-BOT-authored items are never evaluated: the ledger contract
    forbids ``risk_class: ROUTINE`` on human-authored PRs, so a path
    downgrade could never apply anyway, and a forced human hold must
    not be touched by an unattended path classifier.
    """
    changed_paths = item.get("changed_paths")
    return all(
        (
            item.get("lifecycle_state") != "TERMINAL",
            item.get("author_type") == "BOT",
            item.get("current_owner") not in _BLOCKED_OWNERS,
            item.get("guardrail_outcome") in _EVALUATABLE,
            item.get("guardrail_source") not in _PROTECTED_SOURCES,
            isinstance(changed_paths, list) and bool(changed_paths),
        )
    )


def _security_sticky(item: dict[str, Any], sticky: list[str]) -> bool:
    """True when a sticky path class or a SECURITY identity holds the item."""
    return bool(sticky) or item.get("classification") in _SECURITY_CLASSIFICATIONS


def _stand_in_hold(item: dict[str, Any], outcome: Any, sticky: list[str]) -> bool:
    """True for a REVIEW_SECURITY with no sticky evidence (stand-in shape)."""
    return outcome == "REVIEW_SECURITY" and not _security_sticky(item, sticky)


def evaluate_item(
    item: dict[str, Any], clear_standin: bool = False
) -> dict[str, Any] | None:
    """Return a field patch without mutating the item, or None if unchanged.

    Only NOT_RUN/REVIEW_SECURITY or unset outcomes on nonterminal,
    BOT-authored items re-evaluate; items without a nonempty changed_paths
    list keep their current outcome (nothing to classify is not evidence
    of a clean diff). Items owned by
    human/stage2/stage3 or stamped with a protected ``guardrail_source``
    (manual/review/human/octopus) are never touched. A ``REVIEW_SECURITY`` outcome
    downgrades to ``PASS_ROUTINE`` only with ``clear_standin=True`` — a
    recorded hold may come from non-path evidence, so clearing it stays an
    explicit opt-in run by hand, not a recurring stage step.

    A sticky path class or ``classification=SECURITY`` produces
    ``REVIEW_SECURITY`` and ``SENSITIVE``, even with ``clear_standin=True``;
    otherwise the patch sets ``PASS_ROUTINE`` and ``ROUTINE``. The patch
    records sorted taxonomy classes in ``sensitive_paths`` (including
    ``generated_output``, which alone is not sticky) and sets
    ``guardrail_source`` to ``path_eval``. Return None for ineligible items,
    preserved stand-in holds, or items already matching all patch fields.
    """
    if not _evaluable(item):
        return None
    outcome = item.get("guardrail_outcome")
    classes = classify_item_paths(item["changed_paths"])
    sticky = sorted(classes - _STICKY_EXEMPT)
    if _stand_in_hold(item, outcome, sticky) and not clear_standin:
        return None
    sticky_flag = _security_sticky(item, sticky)
    patch = {
        "sensitive_paths": sorted(classes),
        "guardrail_outcome": ("PASS_ROUTINE", "REVIEW_SECURITY")[sticky_flag],
        "guardrail_source": "path_eval",
        "risk_class": ("ROUTINE", "SENSITIVE")[sticky_flag],
    }
    if all(item.get(field) == value for field, value in patch.items()):
        return None
    return patch


def _record_evaluation(
    item: dict[str, Any], patch: dict[str, Any], now: str, summary: dict[str, Any]
) -> None:
    """Apply one item's patch in place and fold it into the summary.

    Set ``updated_at_utc`` to the supplied UTC timestamp ``now``. Patches
    from ``evaluate_item`` leave the event-projected ``revision`` unchanged.
    Count every evaluation; append to ``summary["changes"]`` only when the
    guardrail outcome changes.
    """
    summary["evaluated"] += 1
    outcome = str(patch["guardrail_outcome"])
    summary["by_outcome"][outcome] += 1
    if item.get("guardrail_outcome") == outcome:
        summary["outcomes_unchanged"] += 1
    else:
        summary["changes"].append(
            {
                "key": item.get("key"),
                "from": item.get("guardrail_outcome"),
                "to": outcome,
                "sensitive_paths": patch["sensitive_paths"],
            }
        )
    item.update(patch)
    # item.revision is a projection of transition events only — bumping it
    # here without logging an event breaks the ledger consistency check.
    item["updated_at_utc"] = now


def evaluate_ledger(
    ledger: dict[str, Any],
    repos_filter: set[str] | None,
    clear_standin: bool = False,
) -> tuple[dict[str, Any], dict[str, Any]]:
    """Apply evaluate_item across items; return (ledger, summary)."""
    summary: dict[str, Any] = {
        "evaluated": 0,
        "outcomes_unchanged": 0,
        "skipped": 0,
        "by_outcome": {"REVIEW_SECURITY": 0, "PASS_ROUTINE": 0},
        "changes": [],
    }
    now = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
    for item in ledger.get("items") or []:
        if not isinstance(item, dict):
            continue
        if repos_filter and item.get("repository") not in repos_filter:
            continue
        patch = evaluate_item(item, clear_standin)
        if patch is None:
            summary["skipped"] += 1
            continue
        _record_evaluation(item, patch, now, summary)
    return ledger, summary


def run_guardrails(args: argparse.Namespace) -> int:
    """Fetch the ledger, evaluate items, print or CAS-apply the result."""
    config = load_yaml(CONFIG_PATH)
    taxonomy = (config.get("sensitive_path_taxonomy") or {}).get("classes") or []
    unknown = {name for name, _ in _PATH_RULES} - set(taxonomy)
    if unknown:
        raise ValueError(f"path rules use unknown taxonomy classes: {sorted(unknown)}")
    repos_filter = set(args.repos_filter) if args.repos_filter else None
    with tempfile.TemporaryDirectory(prefix="pr-lifecycle-guardrails-") as tmp:
        ledger_path = Path(tmp) / "ledger.yaml"
        cas.run_preflight(ledger_path)
        ledger = load_yaml(ledger_path)
        ledger, summary = evaluate_ledger(ledger, repos_filter, args.clear_standin)
        summary["dry_run"] = not args.apply
        summary["ledger_revision"] = ledger.get("ledger_revision")
        if args.apply and summary["evaluated"]:
            ledger_path.write_text(dump_ledger(ledger), encoding="utf-8")
            committed = cas.run_commit(ledger_path, _COMMIT_MESSAGE, bump_revision=True)
            summary["commit_sha"] = committed.get("commit_sha")
        print(json.dumps(summary, indent=2, sort_keys=True))
    return 0


def build_parser() -> argparse.ArgumentParser:
    """Build the guardrails CLI parser."""
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--apply", action="store_true")
    parser.add_argument("--repo", action="append", dest="repos_filter")
    parser.add_argument(
        "--json",
        action="store_true",
        dest="json_out",
        help="accepted for stage-prompt parity; output is always JSON",
    )
    parser.add_argument(
        "--clear-stand-in",
        action="store_true",
        dest="clear_standin",
        help=(
            "allow REVIEW_SECURITY outcomes to downgrade to PASS_ROUTINE "
            "when no sticky path class matches (corrects the Stage 1 "
            "stand-in over-marking; human/stage-owned items are never "
            "touched either way)"
        ),
    )
    return parser


def main(argv: list[str] | None = None) -> int:
    """Run the guardrails CLI; return one on handled failures."""
    args = build_parser().parse_args(argv)
    try:
        return run_guardrails(args)
    except (OSError, ValueError, KeyError, TypeError) as exc:
        print(f"PR_LIFECYCLE_GUARDRAILS_ERROR: {type(exc).__name__}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
