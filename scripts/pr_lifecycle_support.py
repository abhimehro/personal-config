"""Small shared value and format checks for PR lifecycle validation."""

from __future__ import annotations

import re
from pathlib import Path
from typing import Any
from urllib.parse import urlparse

ROOT = Path(__file__).resolve().parents[1]
KEY_RE = re.compile(r"^[A-Za-z0-9_.-]+/[A-Za-z0-9_.-]+#[1-9][0-9]*@[0-9a-f]{40}$")
SHA_RE = re.compile(r"^[0-9a-f]{40}$")
UTC_RE = re.compile(r"^\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}(?:\.\d+)?Z$")
URL_RE = re.compile(r"^https://[^\s]+$")


class ArtifactValidationError(ValueError):
    """A fail-closed lifecycle source or runtime-artifact validation error."""


def require_mapping(value: Any, label: str) -> dict[str, Any]:
    if not isinstance(value, dict):
        raise ArtifactValidationError(f"{label}: expected mapping")
    return value


def require_list(value: Any, label: str) -> list[Any]:
    if not isinstance(value, list):
        raise ArtifactValidationError(f"{label}: expected list")
    return value


def require_fields(
    value: dict[str, Any],
    allowed: set[str],
    required: set[str],
    label: str,
) -> None:
    unknown = set(value) - allowed
    missing = required - set(value)
    if unknown:
        raise ValueError(f"{label}: unsupported fields: {sorted(unknown)}")
    if missing:
        raise ValueError(f"{label}: missing required fields: {sorted(missing)}")


def require_utc(value: Any, label: str) -> None:
    if not isinstance(value, str) or not UTC_RE.fullmatch(value):
        raise ValueError(f"{label}: expected RFC 3339 UTC timestamp")


def require_https_url(value: Any, label: str) -> None:
    if not isinstance(value, str) or not URL_RE.fullmatch(value):
        raise ValueError(f"{label}: expected complete https URL")
    parsed = urlparse(value)
    if parsed.scheme != "https" or not parsed.netloc:
        raise ValueError(f"{label}: expected complete https URL")


def require_https_urls(value: Any, label: str) -> None:
    for index, url in enumerate(require_list(value, label)):
        require_https_url(url, f"{label}[{index}]")
