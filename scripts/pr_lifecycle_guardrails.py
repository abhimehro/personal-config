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
_MANUAL_OUTCOMES = {
    "PASS_ROUTINE",
    "HOLD_CONTRACT",
    "HOLD_EVIDENCE",
    "HOLD_PLATFORM",
    "HOLD_CANONICAL",
    "CLOSE_NONSECURITY_NOOP",
    "ANALYSIS_ERROR",
}

# (taxonomy class, regex matched against each changed path). Patterns are
# anchored per path segment; order matters only for readability.
_PATH_RULES: tuple[tuple[str, str], ...] = (
    (
        "workflows_and_permissions",
        r"\.github/(workflows|actions|rulesets|CODEOWNERS|dependabot\.ya?ml|pull_request_template)",
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
        r"(^|/)(package-lock\.json|yarn\.lock|pnpm-lock\.ya?ml|uv\.lock|poetry\.lock|Pipfile\.lock|Gemfile\.lock|go\.(mod|sum)|Cargo\.(toml|lock)|composer\.(json|lock)|requirements[^/]*\.txt|pyproject\.toml|setup\.(py|cfg)|package\.json|Brewfile[^/]*|[^/]*\.gemspec|renv\.lock)",
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
        r"(^|/)(\.gitignore|\.gitattributes|\.cursorignore|\.cursor/|\.devin/|\.idea/|\.vscode/|[^/]*ignore)$",
    ),
    (
        "generated_output",
        r"(^|/)(\.jules/|jules/|generated/|dist/|build/|coverage/|\.snapshot[^/]*|docs/cursor-automations/exports/|[^/]*\.generated\.[^/]*$)",
    ),
    (
        "public_api_contracts",
        r"(^|/)(openapi[^/]*|swagger[^/]*|schemas?/|api[^/]*\.(json|ya?ml)|[^/]*\.proto$|[^/]*\.graphql|[^/]*\.schema\.json)",
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


def evaluate_item(item: dict[str, Any]) -> dict[str, Any] | None:
    """Return the field patch for one item, or None when it is left alone.

    Only NOT_RUN/REVIEW_SECURITY outcomes on nonterminal items re-evaluate;
    items without changed_paths keep their current outcome (nothing to
    classify is not evidence of a clean diff).
    """
    if item.get("lifecycle_state") == "TERMINAL":
        return None
    outcome = item.get("guardrail_outcome")
    if outcome not in _EVALUATABLE:
        return None
    changed_paths = item.get("changed_paths")
    if not isinstance(changed_paths, list) or not changed_paths:
        return None
    classes = classify_item_paths(changed_paths)
    sticky = sorted(classes - _STICKY_EXEMPT)
    new_outcome = "REVIEW_SECURITY" if sticky else "PASS_ROUTINE"
    patch = {
        "sensitive_paths": sorted(classes),
        "guardrail_outcome": new_outcome,
        "risk_class": "SENSITIVE" if sticky else "ROUTINE",
    }
    if all(item.get(field) == value for field, value in patch.items()):
        return None
    return patch


def evaluate_ledger(
    ledger: dict[str, Any], repos_filter: set[str] | None
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
        patch = evaluate_item(item)
        if patch is None:
            summary["skipped"] += 1
            continue
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
        item["revision"] = int(item.get("revision") or 0) + 1
        item["updated_at_utc"] = now
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
        ledger, summary = evaluate_ledger(ledger, repos_filter)
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
