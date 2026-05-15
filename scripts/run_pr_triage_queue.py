#!/usr/bin/env python3
"""Execute (or dry-run) ``gh pr merge`` / ``gh pr close`` lines from ``tasks/pr-triage.md``.

Reads fenced ``bash`` blocks under the ``## Planned mutations`` section (until the next
top-level ``##`` heading). Uses argv lists and ``subprocess`` without a shell. **Default is
dry-run**; pass ``--execute`` to run commands.

# SECURITY: Allowlist-validated argv before any subprocess call — rejects shell metacharacters
#           and any ``gh`` shape other than ``pr merge`` / ``pr close`` with fixed token layouts.
# NOTE: Working-tree guard is hub-repo hygiene (avoid confusing local edits with remote actions).
"""

from __future__ import annotations

import argparse
import re
import shlex
import subprocess  # nosec B404
import sys
from pathlib import Path

# Heading in tasks/pr-triage.md (suffix may change, e.g. simulation vs executed).
PLANNED_MUTATIONS_HEADING_PREFIX = "## Planned mutations"

REPO_ROOT = Path(__file__).resolve().parent.parent
DEFAULT_TRIAGE = REPO_ROOT / "tasks" / "pr-triage.md"

_REPO_SLUG = re.compile(r"^[a-zA-Z0-9]([a-zA-Z0-9._-]*)/[a-zA-Z0-9]([a-zA-Z0-9._-]*)$")

_BASH_FENCE = re.compile(r"^```bash\s*\n(.*?)^```", re.MULTILINE | re.DOTALL)


def _is_new_top_level_section(line: str) -> bool:
    """True for ``## Foo`` but not ``### bar`` (``###`` still startswith ``##`` in Python)."""
    return line.startswith("## ") and not line.startswith("###")


def slice_planned_mutations_section(markdown: str) -> str:
    """Return markdown after the planned-mutations heading until the next top-level ``##``."""
    lines = markdown.splitlines()
    start: int | None = None
    for i, ln in enumerate(lines):
        if ln.startswith(PLANNED_MUTATIONS_HEADING_PREFIX):
            start = i
            break
    if start is None:
        raise ValueError(
            f"Missing '{PLANNED_MUTATIONS_HEADING_PREFIX}' heading in triage markdown."
        )
    collected: list[str] = []
    for ln in lines[start + 1 :]:
        if _is_new_top_level_section(ln):
            break
        collected.append(ln)
    return "\n".join(collected)


def _reject_shell_injection(line: str) -> None:
    if "\n" in line or "\r" in line:
        raise ValueError("Refusing newline inside command line.")
    for token in (";", "&&", "||", "`", "$(", "${"):
        if token in line:
            raise ValueError(
                f"Refusing shell metacharacters ({token!r}) in line: {line!r}"
            )


def line_to_argv(line: str) -> list[str] | None:
    stripped = line.strip()
    if not stripped or stripped.startswith("#"):
        return None
    if not stripped.startswith("gh "):
        raise ValueError(f"Expected line to start with 'gh ', got: {stripped!r}")
    _reject_shell_injection(stripped)
    return shlex.split(stripped, posix=True)


def validate_gh_argv(argv: list[str]) -> None:
    if len(argv) < 2 or argv[0] != "gh" or argv[1] != "pr":
        raise ValueError(f"Not a gh pr invocation: {argv!r}")
    sub = argv[2]
    if sub == "merge":
        _validate_merge_argv(argv)
    elif sub == "close":
        _validate_close_argv(argv)
    else:
        raise ValueError(
            f"Only 'gh pr merge' and 'gh pr close' are allowed, got: {argv!r}"
        )


def _validate_merge_argv(argv: list[str]) -> None:
    if len(argv) not in (7, 8):
        raise ValueError(f"Unexpected gh pr merge argv length {len(argv)}: {argv!r}")
    if not argv[3].isdigit():
        raise ValueError(f"PR number must be digits: {argv!r}")
    if argv[4] != "--repo" or not _REPO_SLUG.match(argv[5]):
        raise ValueError(f"Invalid --repo for merge: {argv!r}")
    if argv[6] != "--squash":
        raise ValueError(f"Expected --squash at position 6: {argv!r}")
    if len(argv) == 8 and argv[7] != "--delete-branch":
        raise ValueError(f"Unknown trailing flag on merge: {argv!r}")


def _validate_close_argv(argv: list[str]) -> None:
    # gh pr close N --repo owner/name --comment '…'  → 8 argv entries after shlex
    if len(argv) != 8:
        raise ValueError(f"Unexpected gh pr close argv length {len(argv)}: {argv!r}")
    if not argv[3].isdigit():
        raise ValueError(f"PR number must be digits: {argv!r}")
    if argv[4] != "--repo" or not _REPO_SLUG.match(argv[5]):
        raise ValueError(f"Invalid --repo for close: {argv!r}")
    if argv[6] != "--comment":
        raise ValueError(f"Expected --comment at position 6: {argv!r}")
    if not argv[7].strip():
        raise ValueError(f"Empty --comment body: {argv!r}")
    if len(argv[7]) > 8000:
        raise ValueError("--comment body unexpectedly long")


def extract_gh_commands(markdown: str) -> list[list[str]]:
    """Parse all allowlisted ``gh`` commands from planned-mutation bash fences."""
    section = slice_planned_mutations_section(markdown)
    commands: list[list[str]] = []
    for block in _BASH_FENCE.findall(section):
        for raw_line in block.splitlines():
            argv = line_to_argv(raw_line)
            if argv is None:
                continue
            validate_gh_argv(argv)
            commands.append(argv)
    return commands


def assert_clean_git_working_tree(repo_root: Path) -> None:
    proc = subprocess.run(
        ["git", "-C", str(repo_root), "status", "--porcelain"],
        check=False,
        capture_output=True,
        text=True,
    )  # nosec B603 B607 — fixed argv; ``git`` on PATH is intentional
    if proc.returncode != 0:
        print(proc.stderr, file=sys.stderr)
        raise RuntimeError(
            f"git status failed in {repo_root} (exit {proc.returncode}); "
            "refusing to continue without a working-tree check."
        )
    dirty = proc.stdout.strip()
    if dirty:
        raise RuntimeError(
            "Hub repo working tree is not clean. Commit or stash local changes before "
            f"running with --execute, or pass --allow-dirty-working-tree.\n{dirty}"
        )


def run_commands(
    commands: list[list[str]],
    *,
    execute: bool,
    continue_on_error: bool,
) -> int:
    """Dry-run prints argv; execute runs each command. Returns 0 on full success."""
    failures = 0
    for i, argv in enumerate(commands, start=1):
        if not execute:
            print(f"[dry-run {i}/{len(commands)}] {argv!r}")
            continue
        print(f"[execute {i}/{len(commands)}] {argv!r}")
        proc = subprocess.run(
            argv, check=False, capture_output=True, text=True
        )  # nosec B603
        if proc.returncode != 0:
            failures += 1
            print(proc.stdout, end="", file=sys.stderr)
            print(proc.stderr, end="", file=sys.stderr)
            print(
                f"Command failed (exit {proc.returncode}): {argv!r}",
                file=sys.stderr,
            )
            if not continue_on_error:
                return proc.returncode or 1
    if not execute:
        return 0
    return 1 if failures else 0


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description="Dry-run (default) or execute gh merge/close queue from pr-triage.md.",
    )
    parser.add_argument(
        "--file",
        type=Path,
        default=DEFAULT_TRIAGE,
        help=f"Path to triage markdown (default: {DEFAULT_TRIAGE})",
    )
    parser.add_argument(
        "--execute",
        action="store_true",
        help="Actually run gh (default: dry-run only).",
    )
    parser.add_argument(
        "--allow-dirty-working-tree",
        action="store_true",
        help="Skip git cleanliness check (not recommended for --execute).",
    )
    parser.add_argument(
        "--continue-on-error",
        action="store_true",
        help="With --execute, continue after a failing gh command.",
    )
    parser.add_argument(
        "--limit",
        type=int,
        default=0,
        metavar="N",
        help="Process at most N commands (0 = no limit).",
    )
    args = parser.parse_args(argv)

    triage_path: Path = args.file
    if not triage_path.is_file():
        print(f"Not a file: {triage_path}", file=sys.stderr)
        return 2

    markdown = triage_path.read_text(encoding="utf-8")
    try:
        commands = extract_gh_commands(markdown)
    except ValueError as e:
        print(str(e), file=sys.stderr)
        return 2

    if args.limit and args.limit > 0:
        commands = commands[: args.limit]

    if args.execute and not args.allow_dirty_working_tree:
        try:
            assert_clean_git_working_tree(REPO_ROOT)
        except RuntimeError as e:
            print(str(e), file=sys.stderr)
            return 3

    if not commands:
        print("No gh commands found under planned mutations.", file=sys.stderr)
        return 2

    mode = "execute" if args.execute else "dry-run"
    print(f"run_pr_triage_queue: {len(commands)} command(s), mode={mode}")
    rc = run_commands(
        commands,
        execute=bool(args.execute),
        continue_on_error=bool(args.continue_on_error),
    )
    return rc


if __name__ == "__main__":
    raise SystemExit(main())
