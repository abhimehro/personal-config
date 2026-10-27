"""Small helpers for executable-path and head-bound guardrail evidence."""

from __future__ import annotations

import hashlib
import json
import os
import re
from collections.abc import Callable, Sequence
from dataclasses import dataclass
from typing import Any

__all__ = [
    "GuardrailEvidence",
    "content_matches_head",
    "diff_sha256",
    "fetch_guardrail_evidence",
    "has_current_evidence_stamp",
    "has_executable_path",
    "is_executable_path",
    "is_sha40",
    "owner_held_stamp_candidate",
    "required_checks_green",
    "routine_blocked",
    "routine_stamp",
    "routine_stamp_only_patch",
    "unstamped_routine_keys",
]

_NON_EXECUTABLE_SUFFIXES = frozenset(
    {
        ".md",
        ".markdown",
        ".rst",
        ".txt",
        ".adoc",
        ".csv",
        ".tsv",
        ".png",
        ".jpg",
        ".jpeg",
        ".gif",
        ".ico",
        ".webp",
        ".pdf",
        ".log",
    }
)
_EXECUTABLE_TXT_BASENAME_RE = re.compile(
    r"^(cmakelists|constraints.*|requirements.*)\.txt$", re.IGNORECASE
)
_EXECUTABLE_BASENAMES = frozenset(
    {
        "makefile",
        "dockerfile",
        "justfile",
        "rakefile",
        "gnumakefile",
        "gemfile",
        "vagrantfile",
        "jenkinsfile",
        "containerfile",
        "procfile",
        "taskfile",
        "podfile",
        "fastfile",
        "dangerfile",
        "brewfile",
    }
)
_SHELL_RC_BASENAME_RE = re.compile(
    r"^\.?(?:zshrc|zshenv|zprofile|zlogin|zlogout|zsh_aliases|bashrc|"
    r"bash_profile|bash_login|bash_logout|bash_aliases|profile|kshrc|"
    r"mkshrc|cshrc|tcshrc|shrc|aliases|functions|xprofile|xsession|"
    r"xinitrc|envrc|gitconfig)$|"
    r"^[^/]*\.gitconfig$",
    re.IGNORECASE,
)
_GIT_CONFIG_PATH_RE = re.compile(r"(?:^|/)git/config$", re.IGNORECASE)
_NON_EXECUTABLE_SUFFIXLESS_BASENAMES = frozenset(
    {
        "license",
        "licence",
        "copying",
        "notice",
        "authors",
        "contributors",
        "changelog",
        "readme",
        "codeowners",
        "owners",
        "version",
        ".gitignore",
        ".gitattributes",
        ".gitmodules",
        ".gitkeep",
        ".keep",
        ".editorconfig",
        ".dockerignore",
        ".npmignore",
        ".prettierignore",
        ".eslintignore",
        ".trunkignore",
        ".mailmap",
        ".nvmrc",
        ".python-version",
        ".ruby-version",
        ".tool-versions",
    }
)
_SHA40_RE = re.compile(r"^[0-9a-f]{40}$")
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
    head_sha: str | None = None
    diff_sha256: str | None = None


def _advisory_name(name: str, patterns: Sequence[str]) -> bool:
    """Match advisory names exactly or by a trailing-star prefix."""
    return any(
        name.startswith(pattern[:-1]) if pattern.endswith("*") else name == pattern
        for pattern in patterns
        if pattern
    )


def _check_records(checks: Any) -> list[dict[str, Any]] | None:
    """Normalize a GitHub rollup list or GraphQL contexts connection."""
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
    """
    Return whether every non-advisory check has an acceptable conclusion.

    Return True when all required checks pass or every record is advisory.
    Pending, failing, or unknown conclusions return False. None means the
    rollup is missing, unsupported, or contains no mapping records.
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
        return True
    return True


def is_executable_path(path: Any) -> bool:
    """Return whether a changed path names executable source or a script."""
    if not isinstance(path, str) or not path.strip():
        return False
    text = path.strip()
    basename = text.rsplit("/", 1)[-1]
    if _is_executable_name(basename, text):
        return True
    return _is_executable_suffix_or_suffixless_basename(basename)


def _is_executable_name(basename: str, text: str) -> bool:
    """Return whether a basename or Git config path is directly executable."""
    return any(
        (
            basename.lower() in _EXECUTABLE_BASENAMES,
            _SHELL_RC_BASENAME_RE.fullmatch(basename) is not None,
            _GIT_CONFIG_PATH_RE.search(text) is not None,
        )
    )


def _is_executable_suffix_or_suffixless_basename(basename: str) -> bool:
    if _EXECUTABLE_TXT_BASENAME_RE.match(basename):
        return True
    suffix = os.path.splitext(basename.removeprefix("."))[1].lower()
    if suffix:
        return suffix not in _NON_EXECUTABLE_SUFFIXES
    return basename.lower() not in _NON_EXECUTABLE_SUFFIXLESS_BASENAMES


def has_executable_path(paths: Any) -> bool:
    """Return whether a list contains an executable source or script path."""
    return isinstance(paths, list) and any(is_executable_path(path) for path in paths)


def is_sha40(value: Any) -> bool:
    """Return whether value is a lowercase 40-hex SHA."""
    return isinstance(value, str) and _SHA40_RE.fullmatch(value) is not None


def diff_sha256(diff_text: str) -> str:
    """Return the lowercase SHA-256 digest of UTF-8 diff text."""
    return hashlib.sha256(diff_text.encode("utf-8")).hexdigest()


def content_matches_head(evidence: Any, head_sha: Any) -> bool:
    """Return whether fetched diff content is available for this item head."""
    return bool(
        evidence is not None
        and not evidence.diff_fetch_failed
        and evidence.diff_text
        and evidence.head_sha == head_sha
    )


def routine_blocked(item: dict[str, Any], evidence: Any) -> bool:
    """Return whether routine evaluation lacks a valid head-bound basis."""
    head_sha = item.get("head_sha")
    return not is_sha40(head_sha) or (
        has_executable_path(item.get("changed_paths"))
        and not content_matches_head(evidence, head_sha)
    )


def routine_stamp(item: dict[str, Any], evidence: Any) -> dict[str, Any]:
    """Build the evidence stamp for a routine decision."""
    head_sha = item.get("head_sha")
    content_ok = content_matches_head(evidence, head_sha)
    return {
        "head_sha": head_sha,
        "basis": "head_bound_diff" if content_ok else "non_executable_paths",
        "diff_sha256": evidence.diff_sha256 if content_ok else None,
    }


def routine_stamp_only_patch(
    item: dict[str, Any], evidence: Any, sticky_flag: bool
) -> dict[str, Any] | None:
    """Build an evidence-only routine patch for an owner-held item."""
    if sticky_flag:
        return None
    stamp = routine_stamp(item, evidence)
    return (
        None
        if item.get("guardrail_evidence") == stamp
        else {"guardrail_evidence": stamp}
    )


def has_current_evidence_stamp(item: dict[str, Any]) -> bool:
    """Return whether the item's evidence stamp matches its current head."""
    stamp = item.get("guardrail_evidence")
    return _stamp_head_current(item, stamp) and _stamp_basis_sufficient(item, stamp)


def _stamp_head_current(item: dict[str, Any], stamp: Any) -> bool:
    return (
        isinstance(stamp, dict)
        and is_sha40(stamp.get("head_sha"))
        and stamp.get("head_sha") == item.get("head_sha")
    )


def _stamp_basis_sufficient(item: dict[str, Any], stamp: Any) -> bool:
    return isinstance(stamp, dict) and (
        stamp.get("basis") == "head_bound_diff"
        or not has_executable_path(item.get("changed_paths") or [])
    )


def owner_held_stamp_candidate(
    item: dict[str, Any],
    blocked_owners: frozenset[str],
    protected_sources: frozenset[str],
    sentinel_standin: Callable[[dict[str, Any]], bool],
) -> bool:
    """Return whether an owner-held routine item may receive only a stamp."""
    changed_paths = item.get("changed_paths")
    source = item.get("guardrail_source")
    protected_source = source in protected_sources and not sentinel_standin(item)
    owner_held = item.get("current_owner") in blocked_owners or protected_source
    return all(
        (
            item.get("lifecycle_state") != "TERMINAL",
            item.get("author_type") == "BOT",
            item.get("risk_class") != "HUMAN_REVIEW",
            item.get("guardrail_outcome") == "PASS_ROUTINE",
            owner_held,
            isinstance(changed_paths, list) and bool(changed_paths),
            not has_current_evidence_stamp(item),
        )
    )


def unstamped_routine_keys(items: Any) -> list[str]:
    """Return sorted keys of nonterminal routine items without a current stamp."""
    return sorted(
        str(item.get("key") or "")
        for item in items or []
        if isinstance(item, dict)
        and item.get("key")
        and item.get("lifecycle_state") != "TERMINAL"
        and item.get("guardrail_outcome") == "PASS_ROUTINE"
        and not has_current_evidence_stamp(item)
    )


def _live_view_payload(view: Any, head_sha: Any) -> dict[str, Any] | None:
    """Parse a successful PR view only when it is anchored to the requested head."""
    if view is None or view.returncode:
        return None
    try:
        payload = json.loads(view.stdout)
    except json.JSONDecodeError:
        return None
    if not isinstance(payload, dict) or payload.get("headRefOid") != head_sha:
        return None
    return payload


def _diff_response_is_usable(response: Any) -> bool:
    return bool(
        response is not None and not response.returncode and response.stdout.strip()
    )


def _fetch_head_bound_diff(
    repo: str,
    base_sha: str,
    head_sha: str,
    capture: Callable[[list[str]], Any],
) -> str | None:
    """Fetch a compare diff using the item's immutable base/head pair."""
    response = capture(
        [
            "gh",
            "api",
            "-H",
            "Accept: application/vnd.github.diff",
            f"repos/{repo}/compare/{base_sha}...{head_sha}",
        ]
    )
    if not _diff_response_is_usable(response):
        return None
    return response.stdout


def _fetch_live_view_payload(
    repo: str,
    pull_number: int,
    head_sha: str,
    capture: Callable[[list[str]], Any],
) -> dict[str, Any] | None:
    response = capture(
        [
            "gh",
            "pr",
            "view",
            str(pull_number),
            "--repo",
            repo,
            "--json",
            "title,mergeable,statusCheckRollup,headRefName,headRefOid",
        ]
    )
    return _live_view_payload(response, head_sha)


def _valid_pr_number(value: Any) -> bool:
    return isinstance(value, int) and not isinstance(value, bool)


def _evidence_identity(item: dict[str, Any]) -> tuple[str, int, str, str] | None:
    repo = str(item.get("repository") or "")
    pull_number = item.get("pr")
    head_sha = item.get("head_sha")
    base_sha = item.get("base_sha")
    if not (repo and isinstance(pull_number, int) and _valid_pr_number(pull_number)):
        return None
    if not (isinstance(head_sha, str) and isinstance(base_sha, str)):
        return None
    if not (is_sha40(head_sha) and is_sha40(base_sha)):
        return None
    return repo, pull_number, head_sha, base_sha


def _digested_head_bound_diff(
    repo: str,
    base_sha: str,
    head_sha: str,
    capture: Callable[[list[str]], Any],
) -> tuple[str, str | None] | None:
    diff_text = _fetch_head_bound_diff(repo, base_sha, head_sha, capture)
    if diff_text is None:
        return None
    return diff_text, diff_sha256(diff_text)


def fetch_guardrail_evidence(
    item: dict[str, Any],
    advisory_patterns: Sequence[str],
    capture: Callable[[list[str]], Any],
    *,
    include_diff: bool = True,
) -> GuardrailEvidence:
    """
    Fetch live guardrail evidence with diffs pinned to the item's SHAs.

    With include_diff=False, skip the diff request and return empty diff_text.
    A missing repository, invalid SHA, command failure, or invalid view JSON
    returns evidence with diff_fetch_failed=True. The live head must match
    the item's head before the compare API is called.
    """
    identity = _evidence_identity(item)
    if identity is None:
        return GuardrailEvidence(diff_fetch_failed=True)
    repo, pull_number, head_sha, base_sha = identity
    payload = _fetch_live_view_payload(repo, pull_number, head_sha, capture)
    if payload is None:
        return GuardrailEvidence(diff_fetch_failed=True)
    diff = (
        _digested_head_bound_diff(repo, base_sha, head_sha, capture)
        if include_diff
        else ("", None)
    )
    if diff is None:
        return GuardrailEvidence(diff_fetch_failed=True)
    diff_text, digest = diff
    return GuardrailEvidence(
        diff_text=diff_text,
        diff_fetch_failed=False,
        required_checks_green=required_checks_green(
            payload.get("statusCheckRollup"), advisory_patterns
        ),
        mergeable=payload.get("mergeable") == "MERGEABLE",
        title=str(payload.get("title") or ""),
        head_ref=str(payload.get("headRefName") or ""),
        head_sha=head_sha,
        diff_sha256=digest,
    )
