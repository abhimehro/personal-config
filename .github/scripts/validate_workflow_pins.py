#!/usr/bin/env python3
"""Fail-closed gate: every remote GitHub Actions `uses:` reference must be pinned to a full commit SHA.

Local actions (``./...``) and Docker images (``docker://...``) are allowed. Any
placeholder text, floating tag, or abbreviated ref causes a non-zero exit.
"""

from __future__ import annotations

import argparse
import re
import sys
from pathlib import Path

# Matches `uses: owner/action@ref # optional comment`, allowing subdir actions
# like `github/codeql-action/init`.
_USES_PATTERN = re.compile(
    r"(?P<prefix>uses:\s*)(?P<action>[^@\s]+)@(?P<ref>[^\s#]+)"
    r"(?:[ \t]+#[ \t]*(?P<comment>[^\n]*))?"
)

_COMMIT_SHA_PATTERN = re.compile(r"^[0-9a-fA-F]{40}$")


def _is_allowed(action: str, ref: str) -> bool:
    """Return True for local paths, Docker images, or full 40-character SHAs."""
    if action.startswith(("./", "docker://")):
        return True
    return bool(_COMMIT_SHA_PATTERN.fullmatch(ref))


def _is_comment_line(line: str) -> bool:
    """Return True if the line is a YAML comment (ignoring leading whitespace)."""
    return line.lstrip().startswith("#")


def validate_file(path: Path) -> list[str]:
    """Return a list of violation messages for a single workflow/action file."""
    violations: list[str] = []
    text = path.read_text(encoding="utf-8")
    for line_no, line in enumerate(text.splitlines(), start=1):
        if _is_comment_line(line):
            continue
        match = _USES_PATTERN.search(line)
        if not match:
            continue
        action = match.group("action")
        ref = match.group("ref")
        if _is_allowed(action, ref):
            continue
        if "<" in ref or ">" in ref or "FULL_40_CHAR" in ref:
            violations.append(
                f"{path}:{line_no}: placeholder or malformed ref in remote action: "
                f"{action}@{ref}"
            )
        else:
            violations.append(
                f"{path}:{line_no}: remote action is not pinned to a full commit SHA: "
                f"{action}@{ref}"
            )
    return violations


def validate_paths(paths: list[Path]) -> int:
    """Scan the given paths and print violations. Return 0 only if clean."""
    violations: list[str] = []
    for path in paths:
        if path.is_file() and path.suffix in {".yml", ".yaml"}:
            violations.extend(validate_file(path))
        elif path.is_dir():
            for child in sorted(path.rglob("*.yml")):
                violations.extend(validate_file(child))
            for child in sorted(path.rglob("*.yaml")):
                violations.extend(validate_file(child))

    if violations:
        print("Workflow action pin violations found:")
        for violation in violations:
            print(f"  - {violation}")
        return 1

    print("All remote GitHub Actions references are pinned to full commit SHAs.")
    return 0


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description="Validate that workflow action references are pinned to full SHAs."
    )
    parser.add_argument(
        "paths",
        nargs="*",
        default=[".github/workflows", ".github/actions"],
        help="Files or directories to scan (default: .github/workflows .github/actions)",
    )
    args = parser.parse_args(argv)
    return validate_paths([Path(p) for p in args.paths])


if __name__ == "__main__":
    raise SystemExit(main())
