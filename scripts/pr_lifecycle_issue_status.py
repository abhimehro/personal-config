#!/usr/bin/env python3
"""Pinned GitHub issue mirror for PR pipeline run status.

Best-effort gh issue helpers: locate the pinned status issue by exact title
match, create or edit its body, and render the status payload. Every gh call
uses a fixed argv with --repo pinned; failures raise OSError. A failed or
malformed issue listing also raises OSError rather than falling through to
issue creation, which would pile up duplicate pinned issues whenever `gh
issue list` errors while a status issue already exists. The only caller is
main()'s --status branch, which maps them to a plain exit-1 error — no
TRANSIENT_RETRY classification.
"""

from __future__ import annotations

import json
import subprocess
from typing import Any

PINNED_ISSUE_TITLE = "PR pipeline status"
_ISSUE_REPO = "abhimehro/personal-config"


def issue_body(status: dict[str, Any]) -> str:
    """Render the pinned status-issue body for a stage status dict."""
    condition_line = (
        f"condition: {status['condition']}\n" if status.get("condition") else ""
    )
    return (
        f"<!-- pr-lifecycle-status -->\n"
        f"updated_at_utc: {status['updated_at_utc']}\n"
        f"run_id: {status.get('run_id') or ''}\n"
        f"stage: {status.get('stage') or ''}\n"
        f"ledger_revision: {status.get('ledger_revision') or ''}\n"
        f"reason: {status.get('reason') or ''}\n"
        f"stop_class: {status.get('stop_class') or ''}\n"
        f"signals_status: {status.get('signals_status') or ''}\n"
        f"{condition_line}"
        f"calibration_enabled: false\n"
        f"\n```json\n{json.dumps(status, indent=2, sort_keys=True)}\n```\n"
    )


def _gh_issue(cmd: list[str]) -> subprocess.CompletedProcess[str]:
    """Run gh issue arguments against the fixed repository with a 60-second timeout.

    Capture text output and return nonzero exit codes without raising.
    Process launch errors and timeouts propagate to the caller.
    """
    return subprocess.run(
        ["gh", "issue", *cmd, "--repo", _ISSUE_REPO],
        check=False,
        capture_output=True,
        text=True,
        timeout=60,
    )


def _find_pinned_issue() -> int | None:
    """Return the pinned issue's number; raise on a failed or malformed list.

    Only a well-formed listing with no exact-title row returns None, so
    update_pinned_issue can safely create the issue. Anything else — a gh
    failure, unparseable JSON, a non-list payload, non-dict rows, or an
    exact-title row without an integer number — is raised as OSError rather
    than risk a duplicate pinned issue. Process exceptions propagate.
    """
    listed = _gh_issue(
        [
            "list",
            "--search",
            f'in:title "{PINNED_ISSUE_TITLE}"',
            "--json",
            "number,title",
            "--limit",
            "20",
        ]
    )
    if listed.returncode != 0:
        stderr = (listed.stderr or "").strip()[:200]
        raise OSError(f"gh issue list failed rc={listed.returncode}: {stderr}")
    try:
        rows = json.loads(listed.stdout)
    except json.JSONDecodeError:
        rows = None
    if not isinstance(rows, list):
        raise OSError("gh issue list returned a malformed payload")
    for row in rows:
        if not isinstance(row, dict):
            raise OSError("gh issue list returned a malformed payload")
        if row.get("title") == PINNED_ISSUE_TITLE:
            number = row.get("number")
            if not isinstance(number, int) or isinstance(number, bool):
                raise OSError("gh issue list matched the pinned title without a number")
            return number
    return None


def _upsert_pinned_issue(issue_number: int | None, body: str) -> None:
    """Edit the supplied issue or create the status issue when its number is None.

    Raise OSError on a nonzero exit code, including at most 200 characters of
    stderr. Process launch errors and timeouts propagate without retry.
    """
    if issue_number is not None:
        result = _gh_issue(["edit", str(issue_number), "--body", body])
    else:
        result = _gh_issue(["create", "--title", PINNED_ISSUE_TITLE, "--body", body])
    if result.returncode != 0:
        stderr = (result.stderr or "").strip()[:200]
        raise OSError(f"gh issue update failed rc={result.returncode}: {stderr}")


def update_pinned_issue(status: dict[str, Any]) -> None:
    """Best-effort update of the pinned PR pipeline status issue."""
    _upsert_pinned_issue(_find_pinned_issue(), issue_body(status))
