"""Apply-time guards for reconcile: partial-inventory abort, per-save cap, CAS replan."""

# Kept separate from pr_lifecycle_reconcile so the planner stays unchanged and the
# guards can be tested without GitHub.

from __future__ import annotations

import os
import random
import re
import time
from collections.abc import Callable
from typing import Any

from pr_lifecycle_config import is_excluded

# Report-only actions never mutate the ledger and never count against the cap.
REPORT_ONLY_ACTIONS = frozenset(
    {
        "LIVE_LOOKUP_FAILED",
        "INGEST_SKIPPED",
        "TERMINAL_BUT_OPEN",
        "INVENTORY_FAILED",
        "PATH_BACKFILL_FAILED",
    }
)
DEFAULT_MAX_APPLY = 60
MAX_CAS_ATTEMPTS = 3
BACKOFF_BASE_SECONDS = 20.0
INVENTORY_ABORT_EXIT = 3
CAS_CONFLICT_EXIT = 4
_PROTECTED_GUARDRAIL_SOURCES = frozenset({"manual", "review", "human", "octopus"})
_Exclusions = frozenset[tuple[str | None, int]]
_HoldCheck = Callable[[dict[str, Any], _Exclusions], str | None]


def max_apply_from_env(explicit: int | None = None) -> int:
    """Return the per-save mutation cap (CLI value, then env, then default)."""
    if explicit is not None:
        return max(1, explicit)
    raw = os.environ.get("PR_LIFECYCLE_MAX_APPLY", "")
    try:
        return max(1, int(raw)) if raw.strip() else DEFAULT_MAX_APPLY
    except ValueError:
        return DEFAULT_MAX_APPLY


def _human_review_hold(item: dict[str, Any], _exclusions: _Exclusions) -> str | None:
    if item.get("risk_class") == "HUMAN_REVIEW":
        return "human_review"
    return None


def _protected_source_hold(
    item: dict[str, Any], _exclusions: _Exclusions
) -> str | None:
    source = item.get("guardrail_source")
    if source in _PROTECTED_GUARDRAIL_SOURCES:
        return f"protected_source:{source}"
    return None


def _outcome_hold(item: dict[str, Any], _exclusions: _Exclusions) -> str | None:
    outcome = str(item.get("guardrail_outcome") or "")
    if outcome == "REVIEW_SECURITY" or outcome.startswith("HOLD_"):
        return f"hold_outcome:{outcome}"
    return None


def _security_classification_hold(
    item: dict[str, Any], _exclusions: _Exclusions
) -> str | None:
    if item.get("classification") == "SECURITY":
        return "classification_security"
    return None


def _forced_hold_note(item: dict[str, Any], _exclusions: _Exclusions) -> str | None:
    next_action = str(item.get("next_action") or "")
    if "HUMAN_HOLD" in next_action or "PR Desk forced hold" in next_action:
        return "forced_hold_note"
    return None


def _excluded_hold(item: dict[str, Any], exclusions: _Exclusions) -> str | None:
    if is_excluded(str(item.get("repository") or ""), item.get("pr"), exclusions):
        return "excluded"
    return None


_HOLD_CHECKS: tuple[_HoldCheck, ...] = (
    _human_review_hold,
    _protected_source_hold,
    _outcome_hold,
    _security_classification_hold,
    _forced_hold_note,
    _excluded_hold,
)


def stale_close_hold_reason(
    item: dict[str, Any], exclusions: _Exclusions
) -> str | None:
    """Return the first marker that prevents stale-closing this ledger item."""
    return next(
        (reason for check in _HOLD_CHECKS if (reason := check(item, exclusions))),
        None,
    )


def action_priority(action: dict[str, Any]) -> int:
    """Lower sorts first: terminal bookkeeping, stale closes, re-anchors, intake."""
    name = str(action.get("action", ""))
    if name.startswith("TERMINAL_"):
        return 0
    if name == "CLOSE_STALE":
        return 1
    if name in {"REANCHOR_HEAD", "SHA_DRIFT_REINTAKE"}:
        return 2
    if name == "INGEST_OPEN_PR":
        return 4
    return 3


def select_batch(
    actions: list[dict[str, Any]], cap: int
) -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
    """Split actions into (selected, deferred) with at most cap mutating actions."""
    # Report-only actions are always kept so the plan still reports them. The
    # sort is stable, so the planner's order holds within a priority band.
    report = [a for a in actions if a.get("action") in REPORT_ONLY_ACTIONS]
    mutating = [a for a in actions if a.get("action") not in REPORT_ONLY_ACTIONS]
    mutating.sort(key=action_priority)
    return report + mutating[:cap], mutating[cap:]


def backoff_seconds(attempt: int, *, rng: Any = random.random) -> float:
    """Jittered exponential backoff: ~20s, ~40s, ~80s for attempts 1..3."""
    base = BACKOFF_BASE_SECONDS * (2 ** (attempt - 1))
    return base * (0.75 + 0.5 * rng())


# Patchable sleep reference for tests.
sleep = time.sleep

_JULES_JOURNAL_RE = re.compile(r"(^|/)\.jules/[^/]+\.md$", re.IGNORECASE)
_WORKFLOW_PATH_RE = re.compile(r"^\.github/workflows/[^/]+\.ya?ml$", re.IGNORECASE)
_DEPENDENCY_PATH_RE = re.compile(
    r"(^|/)(package-lock\.json|yarn\.lock|pnpm-lock\.ya?ml|uv\.lock|poetry\.lock|"
    r"Pipfile\.lock|Gemfile\.lock|go\.(mod|sum)|Cargo\.(toml|lock)|composer\.(json|lock)|"
    r"requirements[^/]*\.txt|requirements/|pyproject\.toml|setup\.(py|cfg)|package\.json|"
    r"Brewfile[^/]*|[^/]*\.gemspec|renv\.lock)$",
    re.IGNORECASE,
)
_TEST_PATH_RE = re.compile(
    r"(?:(?:^|/)tests?/)|(?:(?:^|/)test_[^/]+)|(?:Tests\.(?:swift|py|ts|js)$)",
    re.IGNORECASE,
)
_SECURITY_MODULE_RE = re.compile(
    r"(^|/)(security|safe_http|[^/]*Sanitizer|ApplicationSecurity|"
    r"DomainMutationPolicy|ProcessLauncher|MCPTerminalRecord)\.(py|swift|ts|js|go|rb|sh)$",
    re.IGNORECASE,
)
_STICKY_PATH_PATTERNS: tuple[tuple[str, re.Pattern[str]], ...] = (
    (
        "workflows_and_permissions",
        re.compile(
            r"(^|/)\.github/(workflows|actions|rulesets|scripts|hooks|agents|commands|"
            r"copilot|jules|CODEOWNERS|github-app\.ya?ml|repository-automation\.ya?ml|"
            r"dependabot\.ya?ml|pull_request_template)|(^|/)(\.claude/|\.agents/|"
            r"\.windsurf/|\.codeium/|\.mcp\.json$|AGENTS\.md$|CLAUDE\.md$|"
            r"\.cursorrules$|docs/cursor-automations/(prompts|exports)/)",
            re.IGNORECASE,
        ),
    ),
    (
        "secrets",
        re.compile(
            r"(^|/)(\.env($|\.)|[^/]*\.env$|secrets?/|credentials?[^/]*|"
            r"[^/]*\.(pem|key|p12|pfx|keystore)$|id_(rsa|ed25519|ecdsa|dsa)|"
            r"\.ssh/|[^/]*netrc)",
            re.IGNORECASE,
        ),
    ),
    (
        "authentication_and_authorization",
        re.compile(
            r"[^/]*(authentication|authorization|oauth|rbac|permission|sso|login)"
            r"[^/]*\.(py|sh|js|ts|ya?ml|json|toml|rb|go|fish)$",
            re.IGNORECASE,
        ),
    ),
    (
        "deployment_and_infrastructure",
        re.compile(
            r"(^|/)(Dockerfile[^/]*|docker-compose[^/]*|\.devcontainer/|deploy[^/]*/|"
            r"infrastructure/|terraform[^/]*|[^/]*\.tf$|fly\.toml|vercel\.json|"
            r"launchd[^/]*|launch-agents/|[^/]*\.plist$|systemd[^/]*|[^/]*\.service$)",
            re.IGNORECASE,
        ),
    ),
    (
        "lockfiles_and_major_dependencies",
        _DEPENDENCY_PATH_RE,
    ),
    (
        "security_configuration",
        re.compile(
            r"(^|/)(\.trunk/|\.github/gitleaks\.toml|[^/]*gitleaks[^/]*|"
            r"[^/]*codeql[^/]*|[^/]*semgrep[^/]*|[^/]*trufflehog[^/]*|"
            r"[^/]*trivy[^/]*|[^/]*snyk[^/]*|\.codacy\.ya?ml|"
            r"[^/]*sonar[^/]*\.(ya?ml|properties)|[^/]*zizmor[^/]*|"
            r"SECURITY\.md|\.github/SECURITY[^/]*)",
            re.IGNORECASE,
        ),
    ),
    (
        "database_migrations",
        re.compile(
            r"(^|/)(migrations?/|alembic[^/]*|[^/]*\.sql$|schema\.prisma|prisma/migrations)",
            re.IGNORECASE,
        ),
    ),
    (
        "network_and_browser_origins",
        re.compile(
            r"[^/]*(dns|network|cors|proxy|origin)[^/]*\.(ya?ml|toml|json|conf|cfg|"
            r"sh|py|js|ts|fish)$|(^|/)(hosts|resolv\.conf|pf\.conf|ctrld[^/]*\.toml|"
            r"nginx[^/]*|[^/]*\.zone$)",
            re.IGNORECASE,
        ),
    ),
    (
        "shell_execution",
        re.compile(
            r"[^/]*\.(sh|bash|zsh|fish|command|bat|ps1)$|(^|/)(Makefile|[^/]*\.mk$|bin/)",
            re.IGNORECASE,
        ),
    ),
    (
        "file_read_write_boundaries",
        re.compile(
            r"(^|/)(\.gitignore|\.gitattributes|\.cursorignore|[^/]*ignore$|"
            r"\.cursor/|\.devin/|\.idea/|\.vscode/)",
            re.IGNORECASE,
        ),
    ),
    (
        "public_api_contracts",
        re.compile(
            r"(^|/)(openapi[^/]*|swagger[^/]*|schemas?/|apis?/|api[^/]*\.(json|ya?ml)|"
            r"[^/]*\.proto$|[^/]*\.graphql|[^/]*\.schema\.json)",
            re.IGNORECASE,
        ),
    ),
    (
        "destructive_data_actions",
        re.compile(
            r"[^/]*(delete|purge|wipe|destroy|truncate|drop|erase)"
            r"[^/]*\.(sh|py|sql|js|ts|rb|fish)$",
            re.IGNORECASE,
        ),
    ),
)
_DIFF_SECURITY_PATTERNS: tuple[re.Pattern[str], ...] = (
    re.compile(
        r"\b(subprocess|os\.system|os\.popen|Popen|exec\(|eval\(|shlex|"
        r"shell\s*=\s*True|run_cmd|parse_repo_name|parse_pr_reference)\b"
    ),
    re.compile(
        r"\b(realpath|commonpath|is_relative_to|Path\([^)]*\)\.resolve|"
        r"os\.path\.abspath|symlink|is_symlink|islink|lstat)\b"
    ),
    re.compile(
        r"\b(authenticate|authorize|oauth|jwt|bearer|rbac|chmod|fchmod|umask|"
        r"setuid|Keychain)\b"
    ),
    re.compile(
        r"\b(api_key|secret_key|private_key|gitleaks|hmac\.compare_digest|"
        r"secrets\.)\b",
        re.IGNORECASE,
    ),
    re.compile(r"\b(?:AKIA[0-9A-Z]{16}|gh[pousr]_\w{20,}|xox[abposr]-[\w-]{10,})\b"),
    re.compile(
        r"\b(allow_redirects|ipaddress|urllib\.parse|SSRF|validate_url|safe_http)\b"
    ),
    re.compile(
        r"\b(sanitize_filename|path_traversal|traversal|CWE-\d+)\b", re.IGNORECASE
    ),
)
_TITLE_SECURITY_HINT_RE = re.compile(
    r"\b(sentinel|security|vuln\w*|cve-\d+|cwe-\d+|xss|csrf|ssrf|injection|"
    r"traversal|sanitiz\w*|hardening|auth\w*|redaction|permission\w*)\b",
    re.IGNORECASE,
)
_SENTINEL_BRANCH_RE = re.compile(r"^(?:sentinel/|sentinel-)", re.IGNORECASE)
# SECURITY: Jules persona titles start with "Sentinel:" (optional emoji).
# A bare word such as redis-sentinel is not this hold.
_SENTINEL_PERSONA_RE = re.compile(r"^\W*sentinel\s*:", re.IGNORECASE)
SENTINEL_HOLD_MARKER = "SENTINEL_SECURITY_HOLD"


def is_jules_journal_path(path: Any) -> bool:
    """Return True when path is a Jules markdown journal (.jules/*.md)."""
    return isinstance(path, str) and bool(_JULES_JOURNAL_RE.search(path.strip()))


def non_journal_paths(changed_paths: Any) -> list[str]:
    """Return non-empty changed paths excluding .jules/*.md journal files."""
    if not isinstance(changed_paths, list):
        return []
    return [
        path.strip()
        for path in changed_paths
        if isinstance(path, str) and path.strip() and not is_jules_journal_path(path)
    ]


def sticky_sensitive_classes(changed_paths: Any) -> list[str]:
    """Return sorted sticky taxonomy classes matched by non-journal paths."""
    classes: set[str] = set()
    for path in non_journal_paths(changed_paths):
        for name, pattern in _STICKY_PATH_PATTERNS:
            if pattern.search(path):
                classes.add(name)
    return sorted(classes)


def has_security_module_path(changed_paths: Any) -> bool:
    """Return True when non-test changed paths include a security/sanitizer module."""
    for path in non_journal_paths(changed_paths):
        if _TEST_PATH_RE.search(path):
            continue
        if _SECURITY_MODULE_RE.search(path):
            return True
    return False


def has_path_security_backing(changed_paths: Any) -> bool:
    """Return whether non-journal paths match sticky classes or security modules.

    Test paths are excluded from security-module matching, but can still
    match sticky classes. Missing or non-list paths provide no backing.
    """
    return bool(sticky_sensitive_classes(changed_paths)) or has_security_module_path(
        changed_paths
    )


def _diff_header_is_scannable(lines: list[str], index: int) -> bool | None:
    """Return scan eligibility if lines[index] opens a file header pair.

    A header is a ``--- a/`` or ``--- /dev/null`` line directly followed by a
    ``+++ b/`` or ``+++ /dev/null`` line; the path of the non-null side decides
    eligibility. Return None when the line is not a header.
    """
    line = lines[index]
    nxt = lines[index + 1] if index + 1 < len(lines) else ""
    if not (line.startswith("--- ") and nxt.startswith("+++ ")):
        return None
    paths = [side[6:].strip() for side in (line, nxt) if side[4:6] in ("a/", "b/")]
    if not paths:
        return None
    return not any(
        is_jules_journal_path(path) or bool(_TEST_PATH_RE.search(path))
        for path in paths
    )


def has_diff_security_backing(diff_text: Any) -> bool:
    """Return whether added or removed lines match security-related patterns.

    A ``--- ``/``+++ `` pair that opens a file section selects the file: tests
    and Jules journals are skipped, and the ``a/`` side covers deleted files
    whose ``+++`` header is ``/dev/null``. Content lines that merely begin with
    ``--`` or ``++`` are still scanned. Lines before any header are eligible
    for matching. Empty or non-string diffs provide no backing.
    """
    if not isinstance(diff_text, str) or not diff_text.strip():
        return False
    lines = diff_text.splitlines()
    scannable = True
    skip_next = False
    for index, line in enumerate(lines):
        if skip_next:
            skip_next = False
            continue
        header = _diff_header_is_scannable(lines, index)
        if header is not None:
            scannable = header
            skip_next = True
        elif scannable and line[:1] in ("+", "-"):
            if any(p.search(line) for p in _DIFF_SECURITY_PATTERNS):
                return True
    return False


def has_security_backing(changed_paths: Any, diff_text: Any = None) -> bool:
    """Return True only when paths or diff content back a SECURITY tag."""
    return has_path_security_backing(changed_paths) or has_diff_security_backing(
        diff_text
    )


def has_title_security_hint(record: dict[str, Any]) -> bool:
    """Return True when title, branch, or next_action carries a security/Sentinel hint."""
    text = " ".join(
        str(record.get(field) or "")
        for field in ("title", "headRefName", "next_action")
    )
    return bool(_TITLE_SECURITY_HINT_RE.search(text))


def infer_nonsecurity_classification(
    item: dict[str, Any], live: dict[str, Any] | None = None
) -> str:
    """Infer DEPENDENCY, CI_INFRA, REFACTOR, or UNKNOWN without security checks.

    Item fields override live fields; falsey changed_paths fall back to live
    paths. Return UNKNOWN for missing, empty, or non-list paths. Otherwise,
    dependency-bot authors take priority, followed by workflow-only and
    dependency-only non-journal paths; all other cases return REFACTOR.
    """
    merged = {**(live or {}), **item}
    raw_paths = merged.get("changed_paths") or (live or {}).get("changed_paths")
    if not isinstance(raw_paths, list) or not raw_paths:
        return "UNKNOWN"
    paths = non_journal_paths(raw_paths)
    author = merged.get("author") or {}
    login = str(author.get("login") if isinstance(author, dict) else author).lower()
    if "dependabot" in login or "renovate" in login:
        return "DEPENDENCY"
    if paths and all(_WORKFLOW_PATH_RE.search(p) for p in paths):
        return "CI_INFRA"
    if paths and all(_DEPENDENCY_PATH_RE.search(p) for p in paths):
        return "DEPENDENCY"
    return "REFACTOR"


def infer_pr_classification(record: dict[str, Any], *, diff_text: Any = None) -> str:
    """Classify a PR/item; title keywords alone never produce SECURITY.

    A title keyword such as 'Sentinel' (a Jules persona name) or 'security'
    may act as a hint, but classification='SECURITY' requires backing from
    changed_paths or diff_text.
    """
    paths = record.get("changed_paths")
    diff = diff_text if diff_text is not None else record.get("diff_text")
    if has_security_backing(paths, diff):
        sticky = set(sticky_sensitive_classes(paths))
        security_classes = {
            "secrets",
            "authentication_and_authorization",
            "security_configuration",
            "network_and_browser_origins",
            "shell_execution",
            "file_read_write_boundaries",
            "destructive_data_actions",
        }
        if (
            has_title_security_hint(record)
            or has_security_module_path(paths)
            or has_diff_security_backing(diff)
            or bool(sticky & security_classes)
        ):
            return "SECURITY"
    return infer_nonsecurity_classification(record)


def is_sentinel_security_pr(record: dict[str, Any]) -> bool:
    """Return whether a record is a Jules Sentinel persona or sentinel/ branch."""
    branch = str(record.get("headRefName") or record.get("head_ref") or "").strip()
    if _SENTINEL_BRANCH_RE.match(branch):
        return True
    title = str(record.get("title") or "")
    return _SENTINEL_PERSONA_RE.search(title) is not None


def sentinel_record(
    item: dict[str, Any], live: dict[str, Any] | None = None
) -> dict[str, Any]:
    """Merge live title and head ref over the ledger item for Sentinel checks."""
    record = dict(item)
    if isinstance(live, dict):
        title = live.get("title")
        branch = live.get("headRefName")
        if isinstance(title, str) and title:
            record["title"] = title
        if isinstance(branch, str) and branch:
            record["headRefName"] = branch
    return record


def is_forced_security_hold(item: dict[str, Any]) -> bool:
    """Return whether risk, ownership, review source, or hold text blocks clearing.

    Human, Stage 2, and Stage 3 ownership all preserve the security tag.
    A Jules Sentinel persona or sentinel/ branch is also forced, so the
    title-only reclassify cannot clear it.
    """
    next_action = str(item.get("next_action") or "")
    return (
        item.get("risk_class") == "HUMAN_REVIEW"
        or item.get("current_owner") in {"human", "stage2", "stage3"}
        or item.get("guardrail_source") in {"review", "human", "octopus"}
        or "HUMAN_HOLD" in next_action
        or "PR Desk forced hold" in next_action
        or SENTINEL_HOLD_MARKER in next_action
        or is_sentinel_security_pr(item)
    )


def is_title_only_security_hold(item: dict[str, Any]) -> bool:
    """Return whether REVIEW_SECURITY has a source eligible for automatic clearing.

    Exclude forced holds. Accept path_eval, stand_in, or an absent source;
    manual sources require a security-themed or Sentinel title note.
    This check does not examine path or diff backing.
    """
    if item.get("guardrail_outcome") != "REVIEW_SECURITY":
        return False
    if is_forced_security_hold(item):
        return False
    source = item.get("guardrail_source")
    next_action = str(item.get("next_action") or "")
    if source == "manual":
        return "security-themed" in next_action or "Sentinel title" in next_action
    return source in {"path_eval", "stand_in", None}


def evaluate_security_tag_reconcile(
    item: dict[str, Any], *, diff_text: str | None = None
) -> dict[str, Any] | None:
    """Plan reclassification of a nonterminal BOT item's unbacked SECURITY tag.

    Return None for forced holds, missing or empty changed-path lists, or
    path/diff backing. A non-None diff_text overrides the item's diff_text;
    a missing diff provides no backing here. The returned action includes
    the replacement classification and whether REVIEW_SECURITY may clear,
    without mutating the item. PR-number conversion errors propagate.
    """
    if item.get("lifecycle_state") == "TERMINAL":
        return None
    if item.get("author_type") != "BOT" or item.get("classification") != "SECURITY":
        return None
    if is_forced_security_hold(item):
        return None
    paths = item.get("changed_paths")
    if not isinstance(paths, list) or not paths:
        return None
    if has_path_security_backing(paths):
        return None
    effective_diff = diff_text if diff_text is not None else item.get("diff_text")
    if has_diff_security_backing(effective_diff):
        return None
    to_classification = infer_nonsecurity_classification(item)
    return {
        "action": "RECLASSIFY_TITLE_SECURITY",
        "key": str(item.get("key") or ""),
        "repository": str(item.get("repository") or ""),
        "pr": int(item.get("pr") or 0),
        "from_classification": "SECURITY",
        "to_classification": to_classification,
        "sensitive_paths": sticky_sensitive_classes(paths),
        "clear_review_security": is_title_only_security_hold(item),
        "reason": (
            "title keyword alone cannot set SECURITY/REVIEW_SECURITY "
            "without sensitive path or diff backing"
        ),
    }


def reconcile_security_tagging_summary(
    ledger: dict[str, Any],
    *,
    diff_fetcher: Any = None,
) -> dict[str, Any]:
    """Project security counts and proposed item changes without mutating the ledger.

    Count nonterminal dictionary items and return before/after SECURITY and
    REVIEW_SECURITY totals, reclassification counts, and reclassified_items.
    For eligible items lacking a stored diff, call diff_fetcher(repository, pr)
    when supplied; a None result skips that item. Without a fetcher, missing
    diffs provide no backing. Fetcher errors and TypeError or ValueError from
    PR-number conversion propagate.
    """
    items = [
        i
        for i in (ledger.get("items") or [])
        if isinstance(i, dict) and i.get("lifecycle_state") != "TERMINAL"
    ]
    before_security = sum(1 for i in items if i.get("classification") == "SECURITY")
    before_review_sec = sum(
        1 for i in items if i.get("guardrail_outcome") == "REVIEW_SECURITY"
    )
    reclassified: list[dict[str, Any]] = []
    for item in items:
        if item.get("classification") != "SECURITY":
            continue
        paths = item.get("changed_paths")
        diff_text = item.get("diff_text")
        if (
            diff_text is None
            and diff_fetcher is not None
            and isinstance(paths, list)
            and paths
            and not is_forced_security_hold(item)
            and not has_path_security_backing(paths)
        ):
            diff_text = diff_fetcher(str(item.get("repository")), int(item.get("pr")))
            if diff_text is None:
                continue
        action = evaluate_security_tag_reconcile(item, diff_text=diff_text)
        if action is not None:
            reclassified.append(
                {
                    "key": action["key"],
                    "repository": action["repository"],
                    "pr": action["pr"],
                    "url": item.get("url"),
                    "from_classification": "SECURITY",
                    "to_classification": action["to_classification"],
                    "from_outcome": item.get("guardrail_outcome"),
                    "to_outcome": (
                        "PASS_ROUTINE"
                        if action["clear_review_security"]
                        else item.get("guardrail_outcome")
                    ),
                    "changed_paths": non_journal_paths(paths),
                }
            )
    downgraded_reviews = sum(
        1
        for r in reclassified
        if r["from_outcome"] == "REVIEW_SECURITY" and r["to_outcome"] == "PASS_ROUTINE"
    )
    return {
        "nonterminal_count": len(items),
        "before_security_count": before_security,
        "after_security_count": before_security - len(reclassified),
        "before_review_security_count": before_review_sec,
        "after_review_security_count": before_review_sec - downgraded_reviews,
        "reclassified_count": len(reclassified),
        "downgraded_review_security_count": downgraded_reviews,
        "reclassified_items": reclassified,
    }
