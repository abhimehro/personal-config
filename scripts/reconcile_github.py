"""GitHub API interactions for PR lifecycle reconciliation."""

from __future__ import annotations

import json
import subprocess
from typing import Any

from pr_lifecycle_support import SHA_RE


def _enrich_base_sha(repo: str, pr: int) -> str | None:
    """Enrich the base SHA for a PR via GitHub API."""
    base_cmd = [
        "gh",
        "api",
        f"repos/{repo}/pulls/{pr}",
        "--jq",
        ".base.sha",
    ]
    try:
        base = subprocess.run(
            base_cmd, check=False, capture_output=True, text=True, timeout=60
        )
    except (OSError, subprocess.TimeoutExpired):
        return None
    if base.returncode != 0:
        return None
    sha = (base.stdout or "").strip()
    return sha if sha else None


def _gh_pr_view(repo: str, pr: int) -> dict[str, Any] | None:
    """Fetch live PR fields, returning None when the command or payload fails.

    Note: base SHA is enriched via REST ``gh api`` rather than folding
    ``baseRefOid`` into the ``--json`` field list, so a missing base SHA
    fails closed as None instead of silently omitting the drift check.
    """
    cmd = [
        "gh",
        "pr",
        "view",
        str(pr),
        "--repo",
        repo,
        "--json",
        "state,mergedAt,closedAt,headRefOid,headRefName,title,url,mergedBy,labels",
    ]
    try:
        completed = subprocess.run(
            cmd, check=False, capture_output=True, text=True, timeout=60
        )
    except (OSError, subprocess.TimeoutExpired):
        return None
    if completed.returncode != 0:
        return None
    try:
        payload = json.loads(completed.stdout)
    except json.JSONDecodeError:
        return None
    if not isinstance(payload, dict):
        return None
    sha = _enrich_base_sha(repo, pr)
    if sha is None:
        return None
    payload["baseRefOid"] = sha
    return payload


def _gh_pr_files(repo: str, pr_num: int) -> list[str] | None:
    """Fetch the PR's changed-file paths via REST; None on any failure."""
    # Paginates so a large diff cannot silently truncate evidence (a hidden
    # sensitive path must never downgrade a hold). Renames contribute their
    # old path too: `.previous_filename` keeps a file moved OUT of a
    # sensitive location from looking clean. An empty result also returns
    # None: a real open PR always changes at least one file, so an empty
    # list means the evidence could not be trusted. The API caps at 3000
    # files even under pagination with no truncation signal, so hitting the
    # cap fails closed as well.
    cmd = [
        "gh",
        "api",
        f"repos/{repo}/pulls/{pr_num}/files",
        "--paginate",
        "--jq",
        ".[] | .filename, (.previous_filename // empty)",
    ]
    try:
        completed = subprocess.run(
            cmd, check=False, capture_output=True, text=True, timeout=60
        )
    except (OSError, subprocess.TimeoutExpired):
        return None
    if completed.returncode != 0:
        return None
    paths = sorted({line for line in completed.stdout.splitlines() if line})
    if not paths or len(paths) >= 3000:
        return None
    return paths


def _gh_pr_diff(repo: str, pr_num: int) -> str | None:
    """Fetch the PR's unified diff via gh CLI.

    Return None on process launch errors, a 60-second timeout, a nonzero exit
    status, or empty output (an open PR always changes at least one file, so
    empty output is untrusted evidence); otherwise return stdout.
    """
    cmd = ["gh", "pr", "diff", str(pr_num), "--repo", repo]
    try:
        completed = subprocess.run(  # nosec B603
            cmd, check=False, capture_output=True, text=True, timeout=60
        )
    except (OSError, subprocess.TimeoutExpired):
        return None
    if completed.returncode != 0 or not completed.stdout.strip():
        return None
    return completed.stdout