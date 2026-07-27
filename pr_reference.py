"""Shared, strict PR reference parser/validator for PR automation scripts."""

from __future__ import annotations

import re
import sys
from dataclasses import dataclass


class InvalidPrReferenceError(ValueError):
    """Raised when a PR reference cannot be parsed or contains unsafe input."""


# GitHub owner/repo names are alphanumeric, hyphen, underscore, and dot.
# Require first/last character to be alphanumeric to avoid option-like names.
_OWNER_NAME_RE = re.compile(r"^[A-Za-z0-9](?:[A-Za-z0-9_.-]*[A-Za-z0-9])?$")
# Reject whitespace and ASCII control characters anywhere in the raw string.
_CONTROL_OR_SPACE_RE = re.compile(r"[\s\0-\x1f\x7f]")
# Positive decimal integer (no sign, no leading zeros, no whitespace).
_PR_NUMBER_RE = re.compile(r"^[1-9][0-9]*$")


def _check_component(component: str, kind: str) -> None:
    if not component:
        raise InvalidPrReferenceError(f"{kind} is empty")
    if component[0] == "-":
        raise InvalidPrReferenceError(
            f"{kind} starts with an option-like '-': {component!r}"
        )
    if _CONTROL_OR_SPACE_RE.search(component):
        raise InvalidPrReferenceError(
            f"{kind} contains whitespace/control characters: {component!r}"
        )
    if not _OWNER_NAME_RE.match(component):
        raise InvalidPrReferenceError(
            f"{kind} contains invalid characters: {component!r}"
        )


def _split_repo(repo: str) -> tuple[str, str]:
    repo = repo.strip()
    if not repo:
        raise InvalidPrReferenceError("repo reference is empty")
    if _CONTROL_OR_SPACE_RE.search(repo):
        raise InvalidPrReferenceError(
            f"repo reference contains whitespace/control characters: {repo!r}"
        )
    slash_count = repo.count("/")
    if slash_count != 1:
        raise InvalidPrReferenceError(
            f"repo must be exactly owner/name (got {slash_count} '/'): {repo!r}"
        )
    owner, name = repo.split("/", 1)
    _check_component(owner, "owner")
    _check_component(name, "repo name")
    return owner, name


def _parse_pr_number(pr: str) -> int:
    pr = pr.strip()
    if not pr:
        raise InvalidPrReferenceError("PR number is empty")
    if _CONTROL_OR_SPACE_RE.search(pr):
        raise InvalidPrReferenceError(
            f"PR number contains whitespace/control characters: {pr!r}"
        )
    if pr[0] == "-":
        raise InvalidPrReferenceError(
            f"PR number starts with an option-like '-': {pr!r}"
        )
    if not _PR_NUMBER_RE.match(pr):
        raise InvalidPrReferenceError(
            f"PR number must be a positive decimal integer: {pr!r}"
        )
    return int(pr)


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


def _format_location(source: str | None, line: int | None) -> str:
    return f"{source or '<unknown>'}:{line or '?'}"


def parse_repo_name(
    repo: str,
    *,
    source: str | None = None,
    line: int | None = None,
    strict: bool = False,
) -> str | None:
    """Validate a repo name and return ``owner/name``, or skip with a diagnostic."""
    try:
        owner, name = _split_repo(repo)
        return f"{owner}/{name}"
    except InvalidPrReferenceError as exc:
        location = _format_location(source, line)
        if strict:
            raise InvalidPrReferenceError(f"{location}: {exc}") from exc
        print(f"skipping invalid repo name at {location}: {exc}", file=sys.stderr)
        return None


def parse_pr_reference(
    repo: str,
    pr: str,
    *,
    source: str | None = None,
    line: int | None = None,
    strict: bool = False,
) -> PRReference | None:
    """Validate a ``repo`` + ``pr`` pair and return a typed value, or skip with a diagnostic."""
    try:
        return PRReference.from_parts(repo, pr)
    except InvalidPrReferenceError as exc:
        location = _format_location(source, line)
        if strict:
            raise InvalidPrReferenceError(f"{location}: {exc}") from exc
        print(f"skipping invalid PR reference at {location}: {exc}", file=sys.stderr)
        return None
