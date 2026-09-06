"""Shared, strict PR reference parser/validator for PR automation scripts."""

from __future__ import annotations

import re
import sys
from dataclasses import dataclass
from typing import Any, Callable


class InvalidPrReferenceError(ValueError):
    """Raised when a PR reference cannot be parsed or contains unsafe input."""


# GitHub owner/repo names are alphanumeric, hyphen, underscore, and dot.
# Require first/last character to be alphanumeric to avoid option-like names.
_OWNER_NAME_RE = re.compile(r"^[A-Za-z0-9](?:[A-Za-z0-9_.-]*[A-Za-z0-9])?$")
# Reject whitespace and ASCII control characters anywhere in the raw string.
_CONTROL_OR_SPACE_RE = re.compile(r"[\s\0-\x1f\x7f]")
# Positive decimal integer (no sign, no leading zeros, no whitespace).
_PR_NUMBER_RE = re.compile(r"^[1-9][0-9]*$")

_PARSER_LABELS = {
    "_split_repo": "repo name",
    "_parse_pr_number": "PR number",
}


def _format_location(source: str | None, line: int | None) -> str:
    return f"{source or '<unknown>'}:{line or '?'}"


def _validate_component(value: str, kind: str, regex: re.Pattern) -> None:
    """Validate a single value and raise a descriptive error if it is unsafe."""
    if not value:
        raise InvalidPrReferenceError(f"{kind} is empty")
    if _CONTROL_OR_SPACE_RE.search(value):
        raise InvalidPrReferenceError(
            f"{kind} contains whitespace/control characters: {value!r}"
        )
    if not regex.match(value):
        raise InvalidPrReferenceError(f"{kind} contains invalid characters: {value!r}")


def _split_repo(repo: str) -> tuple[str, str]:
    """Split and validate an ``owner/name`` string."""
    repo = repo.strip()
    if not repo:
        raise InvalidPrReferenceError("repo reference is empty")
    if _CONTROL_OR_SPACE_RE.search(repo):
        raise InvalidPrReferenceError(
            f"repo reference contains whitespace/control characters: {repo!r}"
        )
    if repo.count("/") != 1:
        raise InvalidPrReferenceError(
            f"repo must be exactly owner/name (got {repo.count('/')} '/'): {repo!r}"
        )
    owner, _, name = repo.partition("/")
    _validate_component(owner, "owner", _OWNER_NAME_RE)
    _validate_component(name, "repo name", _OWNER_NAME_RE)
    return owner, name


def _parse_pr_number(pr: str) -> int:
    """Validate and parse a positive decimal PR number."""
    pr = pr.strip()
    _validate_component(pr, "PR number", _PR_NUMBER_RE)
    return int(pr)


def _run_parser(
    parser: Callable[[str], Any],
    value: str,
    *,
    loc: tuple[str, int] | None = None,
    strict: bool = False,
) -> Any | None:
    """Run a single-argument parser, printing a diagnostic or raising on invalid input."""
    try:
        return parser(value)
    except InvalidPrReferenceError as exc:
        source, line = loc if loc else (None, None)
        location = _format_location(source, line)
        label = _PARSER_LABELS.get(parser.__name__, parser.__name__)
        if strict:
            raise InvalidPrReferenceError(f"{location}: {exc}") from exc
        print(f"skipping invalid {label} at {location}: {exc}", file=sys.stderr)
        return None


@dataclass(frozen=True, slots=True)
class PRReference:
    owner: str
    name: str
    number: int

    @property
    def repo(self) -> str:
        return f"{self.owner}/{self.name}"

    @property
    def full(self) -> str:
        return f"{self.repo}#{self.number}"

    @classmethod
    def from_parts(cls, repo: str, pr: str) -> "PRReference":
        owner, name = _split_repo(repo)
        number = _parse_pr_number(pr)
        return cls(owner, name, number)

    @classmethod
    def from_string(cls, ref: str) -> "PRReference":
        ref = ref.strip()
        if not ref:
            raise InvalidPrReferenceError("PR reference is empty")
        if "#" not in ref:
            raise InvalidPrReferenceError(
                f"PR reference must be owner/name#number: {ref!r}"
            )
        repo, _, pr = ref.partition("#")
        return cls.from_parts(repo, pr)


def parse_repo_name(
    repo: str,
    *,
    loc: tuple[str, int] | None = None,
    strict: bool = False,
) -> str | None:
    """Validate a repo name and return ``owner/name``, or skip with a diagnostic."""
    result = _run_parser(_split_repo, repo, loc=loc, strict=strict)
    return f"{result[0]}/{result[1]}" if result else None


def parse_pr_reference(
    repo: str,
    pr: str,
    *,
    loc: tuple[str, int] | None = None,
    strict: bool = False,
) -> "PRReference | None":
    """Validate a ``repo`` + ``pr`` pair and return a typed value, or skip with a diagnostic."""
    owner_name = _run_parser(_split_repo, repo, loc=loc, strict=strict)
    if owner_name is None:
        return None
    number = _run_parser(_parse_pr_number, pr, loc=loc, strict=strict)
    if number is None:
        return None
    return PRReference(owner_name[0], owner_name[1], number)
