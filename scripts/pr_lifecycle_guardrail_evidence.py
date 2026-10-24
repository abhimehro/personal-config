"""Small helpers for executable-path and head-bound guardrail evidence."""

from __future__ import annotations

import hashlib
import os
import re
from typing import Any

_EXECUTABLE_SUFFIXES = frozenset(
    {
        ".py",
        ".pyw",
        ".sh",
        ".bash",
        ".zsh",
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
_SCRIPT_DIRECTORY_RE = re.compile(r"(?:^|/)(?:bin|scripts)/")
_SHA40_RE = re.compile(r"^[0-9a-f]{40}$")


def is_executable_path(path: Any) -> bool:
    """Return whether a changed path names executable source or a script."""
    if not isinstance(path, str) or not path.strip():
        return False
    text = path.strip()
    basename = text.rsplit("/", 1)[-1]
    if basename in _EXECUTABLE_BASENAMES:
        return True
    if os.path.splitext(basename)[1].lower() in _EXECUTABLE_SUFFIXES:
        return True
    return not os.path.splitext(basename)[1] and bool(_SCRIPT_DIRECTORY_RE.search(text))


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
