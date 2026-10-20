"""Deterministic guardrail evaluation for lifecycle ledger items.

Classify each nonterminal item's ``changed_paths`` into the
``sensitive_path_taxonomy`` classes from ``tasks/pr-review-agent.config.yaml``,
then write ``sensitive_paths``, ``guardrail_outcome``, and ``risk_class``.

This replaces the Stage 1 stand-in that bulk-marked 127+ items
``REVIEW_SECURITY`` without evaluating paths: items whose paths hit a sticky
class keep ``REVIEW_SECURITY``; paths hitting only ``generated_output`` or no
class become ``PASS_ROUTINE``. A ``classification`` label, including
``SECURITY``, does not hold an item by itself. ``HOLD_PLATFORM``,
``HOLD_CANONICAL``, ``CLOSE_NONSECURITY_NOOP``, ``ANALYSIS_ERROR``, and
``TERMINAL`` items are never touched. ``HOLD_CONTRACT`` and ``HOLD_EVIDENCE``
downgrade only when the new decision is ``PASS_ROUTINE``.

Dry-run by default; ``--apply`` CAS-commits through ``pr_lifecycle_ledger_cas``.
The path rules are heuristic v1 (revision 2026-08-19 taxonomy): a missed
pattern is a policy-revision question, not a code bug — extend ``_PATH_RULES``
rather than special-casing items.
"""

from __future__ import annotations

import argparse
import json
import re
import subprocess  # nosec B404
import sys
import tempfile
from collections.abc import Callable, Sequence
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import pr_lifecycle_ledger_cas as cas
from pr_lifecycle_persist import dump_ledger
from pr_lifecycle_reconcile_guards import (
    SENTINEL_HOLD_MARKER,
    is_sentinel_security_pr,
)
from pr_lifecycle_yaml import load_yaml

ROOT = Path(__file__).resolve().parents[1]
CONFIG_PATH = ROOT / "tasks/pr-review-agent.config.yaml"

_COMMIT_MESSAGE = "chore(lifecycle): deterministic guardrail path evaluation"
_EVALUATABLE = {
    "NOT_RUN",
    "REVIEW_SECURITY",
    "HOLD_CONTRACT",
    "HOLD_EVIDENCE",
    None,
}
_STICKY_EXEMPT = {"generated_output"}
_CLEARABLE_HOLDS = {"REVIEW_SECURITY", "HOLD_CONTRACT", "HOLD_EVIDENCE"}
_FROZEN_HOLDS = {"HOLD_CONTRACT", "HOLD_EVIDENCE"}
_DEPENDABOT_EXEMPT = {
    "workflows_and_permissions",
    "lockfiles_and_major_dependencies",
}
# Owners whose holds must never be rewritten by an unattended evaluator,
# matching the unblock router's blocked-owner set.
_BLOCKED_OWNERS = {"human", "stage2", "stage3"}
# guardrail_source values that mark a hold/outcome recorded by a real review
# (a human or a security reviewer) rather than path evidence. Even
# --clear-stand-in never downgrades these.
_PROTECTED_SOURCES = {"manual", "review", "human", "octopus"}
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
        r"(^|/)(\.trunk/|\.github/gitleaks\.toml|[^/]*gitleaks[^/]*|[^/]*codeql[^/]*|[^/]*semgrep[^/]*|[^/]*trufflehog[^/]*|[^/]*trivy[^/]*|[^/]*snyk[^/]*|\.codacy\.ya?ml|[^/]*sonar[^/]*\.(ya?ml|properties)|[^/]*zizmor[^/]*|SECURITY\.md|\.github/SECURITY[^/]*|security\.py$)",
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
# Journals are documentation. Match the whole suffix so nested
# `.jules/journal/day.md` is included and `.jules/foo.json` is not.
_JULES_JOURNAL_RE = re.compile(r"(^|/)\.jules/.+\.md$", re.IGNORECASE)
_TEST_PATH_RE = re.compile(
    r"(^|/)(tests?|specs?)/|(^|/)test_[^/]+$|[^/]+_test\.[^/]+$|Tests\.swift$",
    re.IGNORECASE,
)
_FAILURE_CONCLUSIONS = frozenset(
    {
        "FAILURE",
        "TIMED_OUT",
        "CANCELLED",
        "ACTION_REQUIRED",
        "STARTUP_FAILURE",
        "ERROR",
    }
)
_OK_CONCLUSIONS = frozenset({"SUCCESS", "SKIPPED", "NEUTRAL", "PASSED"})
_BUMP_RE = re.compile(
    r"from\s+v?(\d+)\.(\d+)\.(\d+)(?:[-+][0-9A-Za-z.]+)?\s+to\s+"
    r"v?(\d+)\.(\d+)\.(\d+)(?:[-+][0-9A-Za-z.]+)?",
    re.IGNORECASE,
)
_USES_RE = re.compile(r"(?i)uses:\s*(\S+)")
_PERMISSION_KEY_RE = re.compile(
    r"(?i)^\s+(?:actions|attestations|checks|contents|deployments|discussions|"
    r"id-token|issues|models|packages|pages|pull-requests|repository-projects|"
    r"security-events|statuses)\s*:"
)
_SHA40_RE = re.compile(r"[0-9a-f]{40}")
_DIFF_FILE_RE = re.compile(r"^\+\+\+ b/(.+)$")
# Added or removed code lines, not titles. Each pattern names an existing
# taxonomy class so the hold stays inside the sensitive-path vocabulary.
# security_configuration covers input validation/sanitization, which has no
# separate class in the taxonomy.
_DIFF_SIGNAL_RULES: tuple[tuple[str, re.Pattern[str]], ...] = (
    (
        "shell_execution",
        re.compile(
            r"subprocess\.|os\.system\s*\(|os\.popen\s*\(|shell\s*=\s*True|"
            r"\beval\s*\(|\bexec\s*\(|\bPopen\s*\(|\b(?:bash|sh)\s+-c\b|"
            r"\brun_cmd\s*\(|posix_spawn",
            re.IGNORECASE,
        ),
    ),
    (
        "authentication_and_authorization",
        re.compile(
            r"login_required|check_password|verify_password|is_authorized|"
            r"permission_required|hmac\.compare_digest|jwt\.(?:decode|encode)|"
            r"\bauthorize\s*\(|def\s+authenticate\b|\boauth\b|"
            r"_AUTH_HEADERS|\bstrip_auth\b|\bauthorizedRoot\b",
            re.IGNORECASE,
        ),
    ),
    (
        "security_configuration",
        re.compile(
            r"\bsanitize(?:d|r|_filename|\w*)\b|html\.escape|markupsafe|"
            r"shlex\.quote|\bbleach\.|defusedxml|escape_html|"
            r"flags\s*=\s*re\.(?:ASCII|A)\b|parse_repo_name|"
            r"parse_pr_reference|DYLD_INSERT_LIBRARIES",
            re.IGNORECASE,
        ),
    ),
    (
        "file_read_write_boundaries",
        re.compile(
            r"os\.path\.realpath|os\.path\.commonpath|\bnormpath\b|"
            r"secure_filename|\.\./|\.\.\\|\bos\.f?chmod\s*\(|\bstat\.S_ISREG\b|"
            r"\blstat\s*\(|standardizedFileURL",
            re.IGNORECASE,
        ),
    ),
    (
        "secrets",
        re.compile(
            r"BEGIN (?:RSA |OPENSSH |EC )?PRIVATE KEY|"
            r"aws_secret_"
            r"access_key|AKIA[0-9A-Z]{16}|AKIA\[0-9A-Z\]|"
            r"\b(?:password|api_key|secret|token)\s*=\s*['\"][^'\"]+['\"]|"
            r"os\.environ[\[\(].*(?:SECRET|TOKEN|PASSWORD|API_KEY)|"
            r"github_pat_|AIzaSy|\bgh[pousr]_|gh\[pousr\]_|"
            r"\bxox[abposr]-|xox\[abposr\]-|://\)?\s*\[\^/\\s:@\]\+:",
            re.IGNORECASE,
        ),
    ),
    (
        "network_and_browser_origins",
        re.compile(
            r"Access-Control-Allow-Origin|allow_origins|cors_allowed|"
            r"\bCORS\s*\(|_should_strip_cross_host|\bredirect_request\b",
            re.IGNORECASE,
        ),
    ),
)


def is_jules_journal(path: str) -> bool:
    """Return whether `path` is a `.jules` markdown journal."""
    return _JULES_JOURNAL_RE.search(path) is not None


def _is_test_path(path: str) -> bool:
    """Return whether `path` is a test file whose fixtures should not trigger diff holds."""
    return _TEST_PATH_RE.search(path) is not None


def is_sentinel_title_standin(item: dict[str, Any]) -> bool:
    """Return whether a manual guardrail_source is the Stage 1 Sentinel-title stand-in."""
    if item.get("guardrail_source") != "manual":
        return False
    next_action = str(item.get("next_action") or "").lower()
    return "security-themed sentinel title" in next_action


def classify_path(path: Any) -> set[str]:
    """Return the taxonomy classes a changed path matches (empty when clean).

    Non-string or blank paths and .jules Markdown journals match no classes.
    Surrounding whitespace is stripped before matching.
    """
    if not isinstance(path, str) or not path.strip():
        return set()
    text = path.strip()
    # SECURITY: journals are docs. Classifying them as generated_output made
    # Sentinel persona notes look like sensitive output.
    if is_jules_journal(text):
        return set()
    return {name for name, pattern in _COMPILED_RULES if pattern.search(text)}


def classify_item_paths(changed_paths: Any) -> set[str]:
    """Union the taxonomy classes across one item's changed paths."""
    if not isinstance(changed_paths, list):
        return set()
    classes: set[str] = set()
    for path in changed_paths:
        classes.update(classify_path(path))
    return classes


def _evaluable(item: dict[str, Any]) -> bool:
    """Return whether a nonterminal BOT item is eligible for path re-evaluation.

    Non-BOT-authored items are never evaluated: the ledger contract
    forbids ``risk_class: ROUTINE`` on human-authored PRs, so a path
    downgrade could never apply anyway, and a forced human hold must
    not be touched by an unattended path classifier. Items carrying
    ``risk_class: HUMAN_REVIEW`` are human holds regardless of author
    type — a path evaluation must never overwrite the hold with a
    routine stamp.
    """
    changed_paths = item.get("changed_paths")
    if SENTINEL_HOLD_MARKER in str(item.get("next_action") or ""):
        return False
    source = item.get("guardrail_source")
    protected_source = source in _PROTECTED_SOURCES and not is_sentinel_title_standin(
        item
    )
    return all(
        (
            item.get("lifecycle_state") != "TERMINAL",
            item.get("author_type") == "BOT",
            item.get("current_owner") not in _BLOCKED_OWNERS,
            item.get("risk_class") != "HUMAN_REVIEW",
            item.get("guardrail_outcome") in _EVALUATABLE,
            not protected_source,
            isinstance(changed_paths, list) and bool(changed_paths),
        )
    )


@dataclass(frozen=True)
class GuardrailEvidence:
    """Live evidence for exemptions that paths alone cannot decide.

    ``diff_text`` is a unified diff. ``diff_fetch_failed`` means a fetch was
    attempted and did not return one; clearing an existing hold then fails
    closed. ``required_checks_green`` is True only when every non-advisory
    check succeeded, skipped, or was neutral. ``mergeable`` is True only for
    GitHub's MERGEABLE state. ``title`` is used to read a Dependabot semver
    bump and is not a security classification.
    """

    diff_text: str | None = None
    diff_fetch_failed: bool = False
    required_checks_green: bool | None = None
    mergeable: bool | None = None
    title: str | None = None
    head_ref: str | None = None


def _advisory_name(name: str, patterns: Sequence[str]) -> bool:
    """Match advisory check names the same way unblock routing does.

    Exact name, or a trailing ``*`` prefix. Kept inline so a guardrail
    decision does not import the unblock router.
    """
    return any(
        name.startswith(pattern[:-1]) if pattern.endswith("*") else name == pattern
        for pattern in patterns
        if pattern
    )


def _check_records(checks: Any) -> list[dict[str, Any]] | None:
    """Normalize a gh rollup list or a GraphQL contexts connection.

    Discard non-mapping entries; return None for an unsupported shape.
    """
    if isinstance(checks, list):
        return [item for item in checks if isinstance(item, dict)]
    if isinstance(checks, dict):
        contexts = checks.get("contexts")
        nodes = contexts.get("nodes") if isinstance(contexts, dict) else None
        if isinstance(nodes, list):
            return [item for item in nodes if isinstance(item, dict)]
    return None


def _check_identity(check: dict[str, Any]) -> tuple[str, str, bool]:
    """Return (name, conclusion, pending) for one rollup record."""
    name = str(check.get("name") or check.get("context") or "")
    conclusion = str(check.get("conclusion") or check.get("state") or "").upper()
    status = str(check.get("status") or "").upper()
    pending = (status not in {"", "COMPLETED"}) or conclusion in {
        "PENDING",
        "EXPECTED",
    }
    return name, conclusion, pending


def required_checks_green(checks: Any, advisory_patterns: Sequence[str]) -> bool | None:
    """Return whether all non-advisory checks have acceptable conclusions.

    Advisory patterns match exact names or prefixes ending in ``*``. Return
    True when every record is advisory, or all remaining checks completed
    with SUCCESS, SKIPPED, NEUTRAL, or PASSED. Pending, failing, or unknown
    conclusions return False. None means the rollup is missing, unsupported,
    or contains no mapping records.
    """
    records = _check_records(checks)
    if not records:
        return None
    saw_required = False
    for check in records:
        name, conclusion, pending = _check_identity(check)
        if _advisory_name(name, advisory_patterns):
            continue
        saw_required = True
        if pending or conclusion in _FAILURE_CONCLUSIONS:
            return False
        if conclusion not in _OK_CONCLUSIONS:
            return False
    if not saw_required:
        # Every reported check was advisory. Required checks did not fail.
        return True
    return True


def _changed_diff_lines(diff_text: str) -> list[tuple[str, str, str]]:
    """Return a list of (path, marker, text) for added and removed diff lines."""
    rows: list[tuple[str, str, str]] = []
    path = ""
    for raw in diff_text.splitlines():
        file_match = _DIFF_FILE_RE.match(raw)
        if file_match:
            path = file_match.group(1)
            continue
        if raw.startswith(("diff ", "--- ", "@@")):
            continue
        if len(raw) >= 1 and raw[0] in "+-" and not raw.startswith(("+++", "---")):
            rows.append((path, raw[0], raw[1:]))
    return rows


def _doc_or_journal(path: str) -> bool:
    """Skip journals and markdown docs when scanning diff behavior."""
    if is_jules_journal(path):
        return True
    lowered = path.lower()
    return lowered.endswith((".md", ".rst", ".markdown"))


def _comment_line(path: str, line: str) -> bool:
    """Ignore comment-only lines so a mention of eval in prose is not a hold."""
    stripped = line.strip()
    if not stripped:
        return True
    if path.endswith(
        (".js", ".ts", ".tsx", ".jsx", ".java", ".c", ".cc", ".go", ".rs", ".swift")
    ):
        return stripped.startswith("//")
    return stripped.startswith("#")


def diff_security_signals(diff_text: str) -> set[str]:
    """Return taxonomy classes for security-behavior changes in a diff.

    Title text is not consulted. Markdown journals and test files are skipped.
    The match is on added or removed code lines.
    """
    if not diff_text:
        return set()
    signals: set[str] = set()
    for path, _marker, line in _changed_diff_lines(diff_text):
        if _doc_or_journal(path) or _is_test_path(path) or _comment_line(path, line):
            continue
        for name, pattern in _DIFF_SIGNAL_RULES:
            if pattern.search(line):
                signals.add(name)
    return signals


def _semver_level(old: tuple[int, int, int], new: tuple[int, int, int]) -> str:
    """Classify one numeric version pair. Downgrades and equals are unknown."""
    if new[0] != old[0]:
        return "major" if new[0] > old[0] else "unknown"
    if new[1] != old[1]:
        return "minor" if new[1] > old[1] else "unknown"
    if new[2] != old[2]:
        return "patch" if new[2] > old[2] else "unknown"
    return "unknown"


def _bump_levels(text: str) -> set[str]:
    """Collect semver bump levels named by Dependabot's from/to phrase."""
    levels: set[str] = set()
    for match in _BUMP_RE.finditer(text):
        old = (int(match.group(1)), int(match.group(2)), int(match.group(3)))
        new = (int(match.group(4)), int(match.group(5)), int(match.group(6)))
        levels.add(_semver_level(old, new))
    return levels


def resolved_bump(title: str | None, diff_text: str | None) -> str | None:
    """Return a resolved minor or patch bump from title or diff text, else None.

    If both sources contain from/to version phrases, their bump-level sets
    must agree. Major bumps, downgrades, equal versions, and no parseable
    bump return None. A mix of minor and patch bumps resolves to minor.
    The title phrase is accepted when the diff does not name a different level,
    because SHA-pin diffs often omit the semver text.
    """
    title_levels = _bump_levels(title or "")
    diff_levels = _bump_levels(diff_text or "")
    if title_levels and diff_levels and title_levels != diff_levels:
        return None
    levels = title_levels or diff_levels
    if not levels or "unknown" in levels or "major" in levels:
        return None
    if "minor" in levels:
        return "minor"
    if levels == {"patch"}:
        return "patch"
    return None


def _is_dependabot(item: dict[str, Any]) -> bool:
    """Return whether the ledger author login contains dependabot, ignoring case."""
    author = item.get("author")
    if not isinstance(author, dict):
        return False
    return "dependabot" in str(author.get("login") or "").lower()


def _only_workflow_paths(paths: Sequence[str]) -> bool:
    """Return whether every path is a workflow YAML file."""
    if not paths:
        return False
    return all(
        path.startswith(".github/workflows/") and path.endswith((".yml", ".yaml"))
        for path in paths
    )


def _only_lockfile_paths(paths: Sequence[str]) -> bool:
    """Return whether every path is only the lockfile taxonomy class."""
    if not paths:
        return False
    for path in paths:
        if classify_path(path) != {"lockfiles_and_major_dependencies"}:
            return False
    return True


def permissions_block_changed(diff_text: str) -> bool:
    """Return whether a diff changes permissions or a recognized permission key.

    Also detect edits within a permissions block visible in hunk context.
    Indented permission keys are detected even without a visible block header.
    """
    in_block = False
    block_indent: int | None = None
    for raw in diff_text.splitlines():
        if raw.startswith(("diff ", "+++", "---", "@@")):
            in_block = False
            block_indent = None
            continue
        if not raw or raw[0] not in "+- ":
            continue
        body = raw[1:]
        if raw[0] in "+-" and _PERMISSION_KEY_RE.match(body):
            return True
        if not body.strip():
            continue
        indent = len(body) - len(body.lstrip(" "))
        stripped = body.strip()
        if re.match(r"(?i)permissions\s*:", stripped):
            if raw[0] in "+-":
                return True
            in_block = True
            block_indent = indent
            continue
        if (
            in_block
            and block_indent is not None
            and indent <= block_indent
            and not stripped.startswith("#")
        ):
            in_block = False
        if in_block and raw[0] in "+-":
            return True
    return False


def _action_pin_ok(ref: str) -> bool:
    """Return whether a ref is a local action or a full 40-hex SHA pin."""
    text = ref.strip().strip("'\"")
    if text.startswith("./"):
        return True
    if "@" not in text:
        return False
    pin = text.rsplit("@", 1)[-1].split("#", 1)[0]
    return _SHA40_RE.fullmatch(pin) is not None


def added_actions_pinned(diff_text: str) -> bool:
    """Return whether every added uses: ref is a full SHA or a local action.

    Return True when no added line contains a uses: ref.
    """
    for _path, marker, line in _changed_diff_lines(diff_text):
        if marker != "+":
            continue
        match = _USES_RE.search(line)
        if match and not _action_pin_ok(match.group(1)):
            return False
    return True


def dependabot_routine_eligible(
    item: dict[str, Any], evidence: GuardrailEvidence | None
) -> bool:
    """Return whether a Dependabot bump qualifies for the routine path exemption.

    Paths must be nonempty and exclusively workflow YAML or exclusively the
    lockfile taxonomy class. Require a resolved minor or patch bump, a fetched
    diff, green non-advisory checks, and a MERGEABLE PR. Workflow bumps also
    require no permission edits and only pinned or local added action refs.
    Missing evidence fails closed because these paths are otherwise sticky.
    """
    paths = item.get("changed_paths")
    if not isinstance(paths, list) or evidence is None or not _is_dependabot(item):
        return False
    workflows = _only_workflow_paths(paths)
    lockfiles = _only_lockfile_paths(paths)
    if workflows == lockfiles:
        # Neither lane, or both at once. Mixed diffs stay held.
        return False
    if evidence.required_checks_green is not True or evidence.mergeable is not True:
        return False
    if evidence.diff_fetch_failed or evidence.diff_text is None:
        return False
    bump = resolved_bump(evidence.title, evidence.diff_text)
    if bump not in {"minor", "patch"}:
        return False
    return not (
        workflows
        and (
            permissions_block_changed(evidence.diff_text)
            or not added_actions_pinned(evidence.diff_text)
        )
    )


def needs_live_evidence(item: dict[str, Any]) -> bool:
    """Return whether path evaluation needs a diff or check rollup.

    Require nonempty changed_paths. Dependabot workflow-only or lockfile-only
    items need evidence; other items with sticky path classes do not. With no
    sticky classes, only SECURITY classifications or clearable holds need it.
    """
    paths = item.get("changed_paths")
    if not isinstance(paths, list) or not paths:
        return False
    path_sticky = classify_item_paths(paths) - _STICKY_EXEMPT
    if _is_dependabot(item) and (
        _only_workflow_paths(paths) or _only_lockfile_paths(paths)
    ):
        return True
    if path_sticky:
        return False
    return (
        item.get("classification") == "SECURITY"
        or item.get("guardrail_outcome") in _CLEARABLE_HOLDS
    )


def _gh_capture(args: list[str]) -> subprocess.CompletedProcess[str] | None:
    """Run a fixed gh argv. None on timeout or exec failure."""
    try:
        return subprocess.run(  # nosec B603
            args,
            check=False,
            capture_output=True,
            text=True,
            timeout=60,
        )
    except (OSError, subprocess.TimeoutExpired):
        return None


def fetch_guardrail_evidence(
    item: dict[str, Any],
    advisory_patterns: Sequence[str],
    *,
    include_diff: bool = True,
) -> GuardrailEvidence:
    """Read title, diff, mergeability, and checks for one ledger item.

    With include_diff=False, skip the diff request and return empty diff_text.
    A missing repository, a non-integer PR, command failures or timeouts, or invalid
    view JSON return evidence with diff_fetch_failed=True so the caller can
    keep the hold. This does not write the ledger.
    """
    repo = str(item.get("repository") or "")
    pr = item.get("pr")
    if not repo or not isinstance(pr, int):
        return GuardrailEvidence(diff_fetch_failed=True)
    view = _gh_capture(
        [
            "gh",
            "pr",
            "view",
            str(pr),
            "--repo",
            repo,
            "--json",
            "title,mergeable,statusCheckRollup,headRefName",
        ]
    )
    if view is None or view.returncode != 0:
        return GuardrailEvidence(diff_fetch_failed=True)
    diff_text = ""
    if include_diff:
        diff_proc = _gh_capture(["gh", "pr", "diff", str(pr), "--repo", repo])
        if diff_proc is None or diff_proc.returncode != 0:
            return GuardrailEvidence(diff_fetch_failed=True)
        diff_text = diff_proc.stdout
    try:
        payload = json.loads(view.stdout)
    except json.JSONDecodeError:
        return GuardrailEvidence(diff_fetch_failed=True)
    if not isinstance(payload, dict):
        return GuardrailEvidence(diff_fetch_failed=True)
    return GuardrailEvidence(
        diff_text=diff_text,
        diff_fetch_failed=False,
        required_checks_green=required_checks_green(
            payload.get("statusCheckRollup"), advisory_patterns
        ),
        mergeable=payload.get("mergeable") == "MERGEABLE",
        title=str(payload.get("title") or ""),
        head_ref=str(payload.get("headRefName") or ""),
    )


def clearance_rule(item: dict[str, Any], patch: dict[str, Any] | None) -> str | None:
    """Name which rule moved a hold to PASS_ROUTINE, if one did."""
    if not isinstance(patch, dict) or patch.get("guardrail_outcome") != "PASS_ROUTINE":
        return None
    if item.get("guardrail_outcome") not in _CLEARABLE_HOLDS:
        return None
    paths = item.get("changed_paths")
    if not isinstance(paths, list):
        return None
    if _is_dependabot(item) and (
        _only_workflow_paths(paths) or _only_lockfile_paths(paths)
    ):
        return "dependabot_routine"
    if (
        paths
        and not (classify_item_paths(paths) - _STICKY_EXEMPT)
        and any(is_jules_journal(path) for path in paths)
    ):
        return "jules_journal"
    if not (classify_item_paths(paths) - _STICKY_EXEMPT):
        return "classification_without_sensitive_path"
    return None


def evaluate_item(
    item: dict[str, Any],
    clear_standin: bool = False,
    evidence: GuardrailEvidence | None = None,
) -> dict[str, Any] | None:
    """Return a field patch without mutating the item, or None if unchanged.

    Only evaluable outcomes on nonterminal BOT items re-evaluate. Items
    without a nonempty changed_paths list keep their outcome. HUMAN_REVIEW
    items and items owned by human/stage2/stage3 are never touched. Protected
    ``guardrail_source`` values (manual/review/human/octopus) are untouched
    except for the manual Stage 1 Sentinel-title stand-in. ``clear_standin``
    is accepted for CLI compatibility and does not gate the downgrade.

    Sticky path classes, except eligible Dependabot exemptions, and supplied
    security-behavior diff signals produce ``REVIEW_SECURITY``. A classification
    label alone does not. Missing evidence permits path-only evaluation; an
    explicitly failed fetch preserves clearable holds and holds SECURITY-labeled
    items. ``HOLD_CONTRACT`` and ``HOLD_EVIDENCE`` stay put when the new decision
    is still a hold.
    """
    del clear_standin  # CLI flag remains; downgrade no longer depends on it.
    if not _evaluable(item):
        return None
    outcome = item.get("guardrail_outcome")
    classes = classify_item_paths(item["changed_paths"])
    path_sticky = classes - _STICKY_EXEMPT
    signals: set[str] = set()
    if evidence is not None and evidence.diff_text:
        signals = diff_security_signals(evidence.diff_text)
    exempt: set[str] = set()
    if dependabot_routine_eligible(item, evidence):
        exempt = path_sticky & _DEPENDABOT_EXEMPT
    effective = (path_sticky - exempt) | signals
    # A Sentinel persona or sentinel/ branch stays REVIEW_SECURITY even when
    # the diff has no other security signal. Title-only reconcile cannot clear it.
    sentinel_hold = evidence is not None and is_sentinel_security_pr(
        {"title": evidence.title, "headRefName": evidence.head_ref}
    )
    fail_closed = bool(
        evidence is not None
        and evidence.diff_fetch_failed
        and not effective
        and (outcome in _CLEARABLE_HOLDS or item.get("classification") == "SECURITY")
    )
    sticky_flag = bool(effective) or fail_closed or sentinel_hold
    if outcome in _FROZEN_HOLDS and sticky_flag:
        return None
    recorded = (set(classes) | signals) - exempt
    if fail_closed and not recorded:
        prior = item.get("sensitive_paths")
        if isinstance(prior, list):
            recorded = {str(value) for value in prior}
    patch = {
        "sensitive_paths": sorted(recorded),
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
    evidence_for: Callable[[dict[str, Any]], GuardrailEvidence | None] | None = None,
) -> tuple[dict[str, Any], dict[str, Any]]:
    """Update ledger items in place; return the same ledger and a summary.

    A nonempty repos_filter limits evaluation to those repositories; None or
    an empty set includes all. If supplied, evidence_for is called for each
    mapping item passing that filter, even if evaluation later skips it.
    Callback errors propagate, leaving any earlier updates in place.

    Applied patches refresh updated_at_utc without changing item revisions or
    events. The summary counts patches and skipped evaluations and lists only
    outcome changes; filtered-out and non-mapping entries are not counted.
    """
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
        evidence = evidence_for(item) if evidence_for is not None else None
        patch = evaluate_item(item, clear_standin, evidence)
        if patch is None:
            summary["skipped"] += 1
            continue
        _record_evaluation(item, patch, now, summary)
    return ledger, summary


def run_guardrails(args: argparse.Namespace) -> int:
    """Fetch the ledger, evaluate items, print JSON, and return zero on success.

    args.repos_filter optionally limits repositories; args.apply persists
    changes through CAS only if at least one item receives a patch. Without
    args.apply, only report proposed changes. Fetch live evidence as needed.

    Raise ValueError if path rules reference unknown taxonomy classes. Errors
    from configuration loading, ledger preflight, and CAS persistence propagate
    to the caller.
    """
    config = load_yaml(CONFIG_PATH)
    taxonomy = (config.get("sensitive_path_taxonomy") or {}).get("classes") or []
    unknown = {name for name, _ in _PATH_RULES} - set(taxonomy)
    if unknown:
        raise ValueError(f"path rules use unknown taxonomy classes: {sorted(unknown)}")
    repos_filter = set(args.repos_filter) if args.repos_filter else None
    unblock = (config.get("lifecycle") or {}).get("unblock") or {}
    advisory = unblock.get("advisory_checks") or []
    if not isinstance(advisory, list):
        advisory = []

    def _evidence_for(item: dict[str, Any]) -> GuardrailEvidence | None:
        # Fetch only when a clean path list would otherwise clear a hold or
        # a Dependabot lane needs checks. Ordinary docs stay offline.
        """Fetch live evidence only when paths and the current hold require it."""
        if not needs_live_evidence(item):
            return None
        return fetch_guardrail_evidence(item, advisory)

    with tempfile.TemporaryDirectory(prefix="pr-lifecycle-guardrails-") as tmp:
        ledger_path = Path(tmp) / "ledger.yaml"
        cas.run_preflight(ledger_path)
        ledger = load_yaml(ledger_path)
        ledger, summary = evaluate_ledger(
            ledger, repos_filter, args.clear_standin, _evidence_for
        )
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
            "accepted for older invocations; a non-sticky REVIEW_SECURITY "
            "now downgrades without this flag. Protected sources and human "
            "holds are still never touched"
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
