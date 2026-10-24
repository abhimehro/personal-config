"""Small helpers for executable-path and head-bound guardrail evidence."""

from __future__ import annotations

import hashlib
import json
import os
import re
from collections.abc import Callable
from typing import Any

_EXECUTABLE_SUFFIXES = frozenset(
    {
        ".py",
        ".pyw",
        ".sh",
        ".bash",
        ".zsh",
        ".ksh",
        ".csh",
        ".tcsh",
        ".cmd",
        ".fish",
        ".js",
        ".mjs",
        ".cjs",
        ".jsx",
        ".ts",
        ".tsx",
        ".rb",
        ".go",
        ".rs",
        ".swift",
        ".r",
        ".pl",
        ".php",
        ".java",
        ".kt",
        ".kts",
        ".ps1",
        ".psm1",
        ".vbs",
        ".lua",
        ".c",
        ".h",
        ".cc",
        ".cpp",
        ".m",
        ".mm",
        ".cs",
        ".scala",
        ".groovy",
        ".gradle",
        ".applescript",
    }
)
_EXECUTABLE_BASENAMES = frozenset({"Makefile", "Dockerfile", "Justfile", "Rakefile"})
_SHELL_RC_BASENAME_RE = re.compile(
    r"^\.?(?:zshrc|zshenv|zprofile|zlogin|zlogout|bashrc|bash_profile|"
    r"bash_login|bash_logout|profile|kshrc|cshrc|tcshrc|envrc|gitconfig)$|"
    r"^[^/]*\.gitconfig$",
    re.IGNORECASE,
)
_GIT_CONFIG_PATH_RE = re.compile(r"(?:^|/)git/config$")
_SCRIPT_DIRECTORY_RE = re.compile(
    r"(?:^|/)(?:bin|scripts|hooks|git-hooks|\.husky)/"
)
_SHA40_RE = re.compile(r"^[0-9a-f]{40}$")


def is_executable_path(path: Any) -> bool:
    """Return whether a changed path names executable source or a script."""
    if not isinstance(path, str) or not path.strip():
        return False
    text = path.strip()
    basename = text.rsplit("/", 1)[-1]
    if (
        basename in _EXECUTABLE_BASENAMES
        or _SHELL_RC_BASENAME_RE.fullmatch(basename)
        or _GIT_CONFIG_PATH_RE.search(text)
    ):
        return True
    if os.path.splitext(basename)[1].lower() in _EXECUTABLE_SUFFIXES:
        return True
    return not os.path.splitext(basename)[1] and bool(_SCRIPT_DIRECTORY_RE.search(text))


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


def has_current_evidence_stamp(item: dict[str, Any]) -> bool:
    stamp = item.get("guardrail_evidence")
    return isinstance(stamp, dict) and stamp.get("head_sha") == item.get("head_sha")


def owner_held_routine_stamp_candidate(
    item: dict[str, Any],
    blocked_owners: frozenset[str],
    protected_sources: frozenset[str],
    sentinel_standin: Callable[[dict[str, Any]], bool],
) -> bool:
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
    if view is None or view.returncode != 0:
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
        response is not None
        and response.returncode == 0
        and response.stdout.strip()
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
