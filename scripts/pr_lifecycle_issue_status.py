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
import re
import subprocess
from collections.abc import Callable, Iterable
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from typing import Any

PINNED_ISSUE_TITLE = "PR pipeline status"
BACKLOG_ISSUE_TITLE = "PR lifecycle: needs human decision"
_ISSUE_REPO = "abhimehro/personal-config"
_BACKLOG_MARKER = "<!-- pr-lifecycle-backlog -->"
# GitHub caps issue bodies at 65,536 chars; reserve room for the marker,
# preamble lines, and the durable-state JSON block.
_BACKLOG_TABLE_CHAR_CAP = 45_000
_STATE_PATTERN = re.compile(r"<!-- pr-lifecycle-backlog-state (\{.*\}) -->")
_DEFAULT_PACKET_EXPIRY_DAYS = 7


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


def _gh_issue(
    cmd: list[str], repo: str = _ISSUE_REPO
) -> subprocess.CompletedProcess[str]:
    """Run gh issue arguments against a pinned repository with 60s timeout.

    Capture text output and return nonzero exit codes without raising.
    Process launch errors and timeouts propagate to the caller.
    """
    return subprocess.run(
        ["gh", "issue", *cmd, "--repo", repo],
        check=False,
        capture_output=True,
        text=True,
        timeout=60,
    )


def _parse_issue_rows(stdout: str) -> Any:
    """Decode an issue-list payload, raising OSError on malformed JSON."""
    try:
        return json.loads(stdout)
    except (TypeError, json.JSONDecodeError) as exc:
        raise OSError("gh issue list returned a malformed payload") from exc


def _dict_rows(rows: Any) -> bool:
    """Require a list whose elements are all dicts."""
    return isinstance(rows, list) and all(isinstance(row, dict) for row in rows)


def _gh_listed_rows(listed: subprocess.CompletedProcess[str]) -> list[Any]:
    """Return a dict-row issue-list payload; raise on failure or malformed JSON."""
    if listed.returncode != 0:
        stderr = (listed.stderr or "").strip()[:200]
        raise OSError(f"gh issue list failed rc={listed.returncode}: {stderr}")
    rows = _parse_issue_rows(listed.stdout)
    if not _dict_rows(rows):
        raise OSError("gh issue list returned a malformed payload")
    return rows


def _list_pinned_rows(repo: str = _ISSUE_REPO) -> list[Any]:
    """Return the bounded issue-list payload; raise on any failed listing."""
    listed = _gh_issue(
        [
            "list",
            "--search",
            f'in:title "{PINNED_ISSUE_TITLE}"',
            "--json",
            "number,title",
            "--state",
            "all",
            "--limit",
            "1000",
        ],
        repo,
    )
    return _gh_listed_rows(listed)


def _pinned_row_number(row: dict[str, Any]) -> int:
    """Return the matched row's issue number; a missing one fails closed."""
    number = row.get("number")
    if not isinstance(number, int) or isinstance(number, bool):
        raise OSError("gh issue list matched the pinned title without a number")
    return number


def _find_pinned_issue(repo: str = _ISSUE_REPO) -> int | None:
    """Return the pinned issue's number; raise on a failed or malformed list.

    Only a well-formed listing with no exact-title row returns None, so
    update_pinned_issue can safely create the issue. Anything else — a gh
    failure, unparseable JSON, a non-list payload, non-dict rows, or an
    exact-title row without an integer number — is raised as OSError rather
    than risk a duplicate pinned issue. Process exceptions propagate.
    """
    for row in _list_pinned_rows(repo):
        if not isinstance(row, dict):
            raise OSError("gh issue list returned a malformed payload")
        if row.get("title") == PINNED_ISSUE_TITLE:
            return _pinned_row_number(row)
    return None


def _upsert_pinned_issue(
    issue_number: int | None, body: str, repo: str = _ISSUE_REPO
) -> None:
    """Edit the supplied issue or create the status issue when its number is None.

    Raise OSError on a nonzero exit code, including at most 200 characters of
    stderr. Process launch errors and timeouts propagate without retry.
    """
    if issue_number is not None:
        result = _gh_issue(["edit", str(issue_number), "--body", body], repo)
    else:
        result = _gh_issue(
            ["create", "--title", PINNED_ISSUE_TITLE, "--body", body], repo
        )
    if result.returncode != 0:
        stderr = (result.stderr or "").strip()[:200]
        raise OSError(f"gh issue update failed rc={result.returncode}: {stderr}")


def update_pinned_issue(status: dict[str, Any]) -> None:
    """Best-effort update of the pinned PR pipeline status issue."""
    _upsert_pinned_issue(_find_pinned_issue(), issue_body(status))


def _list_backlog_rows(repo: str) -> list[Any]:
    """List open backlog issue candidates, raising OSError on invalid results.

    Nonzero exits also raise OSError; process launch errors and timeouts
    propagate to the caller.
    """
    listed = _gh_issue(
        [
            "list",
            "--search",
            f'in:title "{BACKLOG_ISSUE_TITLE}"',
            "--json",
            "number,title,body",
            "--state",
            "open",
            "--limit",
            "1000",
        ],
        repo,
    )
    return _gh_listed_rows(listed)


def _utc(value: datetime) -> datetime:
    """Convert a datetime to UTC, treating naive values as already in UTC."""
    if value.tzinfo is None:
        return value.replace(tzinfo=timezone.utc)
    return value.astimezone(timezone.utc)


def _iso(value: datetime) -> str:
    """Format a datetime as a UTC timestamp with second precision."""
    return _utc(value).strftime("%Y-%m-%dT%H:%M:%SZ")


def _previous_state(body: object) -> dict[str, Any]:
    """Read the last embedded backlog state, defaulting invalid fields to empty."""
    if not isinstance(body, str):
        return {"first_seen": {}, "overdue_notified": []}
    matches = list(_STATE_PATTERN.finditer(body))
    if not matches:
        return {"first_seen": {}, "overdue_notified": []}
    try:
        state = json.loads(matches[-1].group(1))
    except json.JSONDecodeError:
        return {"first_seen": {}, "overdue_notified": []}
    if not isinstance(state, dict):
        return {"first_seen": {}, "overdue_notified": []}
    first_seen = state.get("first_seen")
    notified = state.get("overdue_notified")
    rows_meta = state.get("rows_meta")
    return {
        "first_seen": _migrate_first_seen(first_seen),
        "overdue_notified": (
            [key.split(":", 1)[0] if isinstance(key, str) else key for key in notified]
            if isinstance(notified, list)
            else []
        ),
        "rows_meta": rows_meta if isinstance(rows_meta, dict) else {},
    }


def _migrate_first_seen(first_seen: Any) -> dict[str, Any]:
    """Map legacy repo#pr:blocker keys to repo#pr, keeping the earliest time."""
    migrated: dict[str, Any] = {}
    if not isinstance(first_seen, dict):
        return migrated
    for key, value in first_seen.items():
        if not isinstance(key, str) or not isinstance(value, str):
            continue
        base = key.split(":", 1)[0]
        prev = migrated.get(base)
        if prev is None or value < prev:
            migrated[base] = value
    return migrated


def _row_key(repo: str, row: dict[str, Any]) -> str:
    """Identify a backlog row: one row per repository/PR pair."""
    return f"{repo}#{row.get('pr')}"


def _row_first_seen(
    key: str, previous: dict[str, Any], now_utc: datetime
) -> tuple[str, datetime]:
    """Resolve a row's first-seen timestamp, preserving prior state.

    Return (iso_text, datetime); an absent, non-string, or unparseable
    previous timestamp resolves to now_utc.
    """
    first = previous.get(key)
    if isinstance(first, str):
        try:
            first_at = _utc(datetime.fromisoformat(first.replace("Z", "+00:00")))
            return _iso(first_at), first_at
        except ValueError:
            pass
    return _iso(now_utc), now_utc


def _valid_days(value: Any) -> bool:
    """Require a positive int day count (bool excluded)."""
    return isinstance(value, int) and not isinstance(value, bool) and value >= 1


def _packet_expiry_days(row: dict[str, Any]) -> int:
    """Return the row's close-days value, defaulting when absent or invalid."""
    days = row.get("packet_expiry_close_days", _DEFAULT_PACKET_EXPIRY_DAYS)
    return days if _valid_days(days) else _DEFAULT_PACKET_EXPIRY_DAYS


def _expiry_text(row: dict[str, Any], first_at: datetime) -> str:
    """Return the row's expires text, deriving it when absent or empty."""
    expiry_text = row.get("expires")
    if isinstance(expiry_text, str) and expiry_text:
        return expiry_text
    return _iso(first_at + timedelta(days=_packet_expiry_days(row)))


def _row_expiry(row: dict[str, Any], first_at: datetime) -> tuple[str, datetime]:
    """Resolve a row's expiry as (iso_text, datetime).

    A missing/empty expiry derives from packet_expiry_close_days
    (default seven days); an unparseable one uses seven days from
    first seen.
    """
    expiry_text = _expiry_text(row, first_at)
    try:
        return expiry_text, _utc(
            datetime.fromisoformat(expiry_text.replace("Z", "+00:00"))
        )
    except ValueError:
        expiry_at = first_at + timedelta(days=_DEFAULT_PACKET_EXPIRY_DAYS)
        return _iso(expiry_at), expiry_at


def _find_backlog_issue(rows: list[Any]) -> dict[str, Any] | None:
    """Return the first row titled as the backlog issue.

    Every title-matching row must carry an integer number; a missing or
    boolean number raises OSError so a malformed listing fails closed
    rather than shadowing the real issue.
    """
    issue: dict[str, Any] | None = None
    for row in rows:
        if row.get("title") != BACKLOG_ISSUE_TITLE:
            continue
        if issue is None:
            issue = row
        number = row.get("number")
        if not isinstance(number, int) or isinstance(number, bool):
            raise OSError("gh issue list matched backlog title without a number")
    return issue


def _markdown_cell(value: object, limit: int = 300) -> str:
    """Bound cell text and neutralize pipes, comment markers, and mentions."""
    text = " ".join(str(value or "").replace("|", "\\|").split())
    text = text.replace("<!--", "&lt;!--").replace("-->", "--&gt;")
    text = text.replace("@", "@\u200b")
    return text[:limit]


def _safe_url(value: object) -> str:
    """Strip surrounding whitespace and return a plain https URL, or blank.

    Link destinations must not be cell-escaped (escaping corrupts the href)
    and must not carry markdown (a crafted url could break out of the link).
    """
    text = str(value or "").strip()
    if re.fullmatch(r"https://[^\s()\[\]<>\"'`]+", text):
        return text
    return ""


def _is_handoff_row(row: dict[str, Any]) -> bool:
    """True for rows handed to a non-human owner (e.g. stage2 escalations).

    Rows without an owner, or owned by "human", stay on the human decision
    table with real expiry and overdue state.
    """
    return row.get("owner") not in (None, "human")


def _row_deadline(
    row: dict[str, Any], first_at: datetime, now_utc: datetime
) -> tuple[str, bool]:
    """Expiry text and overdue flag; non-human handoff rows never expire."""
    expiry_text, expiry_at = _row_expiry(row, first_at)
    if _is_handoff_row(row):
        return "—", False
    return expiry_text, now_utc >= expiry_at


def _record_overdue(
    row: dict[str, Any], notified: set[str], newly_overdue: list[dict[str, Any]]
) -> None:
    """Queue a row for its one overdue notification, once per state key."""
    if row["overdue"] and row["id"] not in notified:
        newly_overdue.append(row)
        notified.add(row["id"])


@dataclass(frozen=True)
class _BacklogSpec:
    """Inputs shared by backlog row preparation."""

    repo: str
    state: dict[str, Any]
    now: datetime
    record_overdue: bool = True


def _prepare_backlog_rows(
    spec: _BacklogSpec,
    rows: list[dict[str, Any]],
) -> tuple[list[dict[str, Any]], dict[str, Any], list[dict[str, Any]]]:
    """Deduplicate rows and return prepared rows, state, and new overdue items.

    Preserve first-seen timestamps for active keys, derive missing expiry
    dates, and prune notification state for rows no longer in the backlog.
    Keep the first row per repository/PR/blocker key without changing inputs.
    Absent, empty, or non-string expiry uses packet_expiry_close_days
    (default seven days);
    unparseable expiry strings use seven days from first seen. A row is
    overdue at or after its deadline. Rows with a non-human owner use an
    em dash for expiry and never become overdue; ownerless rows use deadlines.
    Set record_overdue=False to leave new overdue notifications unrecorded.
    """
    now_utc = _utc(spec.now)
    first_seen_before = spec.state.get("first_seen") or {}
    notified = {
        key
        for key in (spec.state.get("overdue_notified") or [])
        if isinstance(key, str)
    }
    first_seen: dict[str, str] = {}
    prepared: list[dict[str, Any]] = []
    newly_overdue: list[dict[str, Any]] = []
    seen: set[str] = set()
    for raw in rows:
        key = _row_key(spec.repo, raw)
        if key in seen:
            continue
        seen.add(key)
        row = dict(raw)
        first, first_at = _row_first_seen(key, first_seen_before, now_utc)
        first_seen[key] = first
        expiry_text, overdue = _row_deadline(row, first_at, now_utc)
        row.update(
            {
                "id": key,
                "first_seen": first,
                "expires": expiry_text,
                "overdue": overdue,
            }
        )
        prepared.append(row)
        if spec.record_overdue:
            _record_overdue(row, notified, newly_overdue)
    new_state = {
        "first_seen": first_seen,
        "overdue_notified": sorted(key for key in notified if key in first_seen),
        "rows_meta": _rows_meta(prepared),
    }
    return prepared, new_state, newly_overdue


def _rows_meta(prepared: list[dict[str, Any]]) -> dict[str, dict[str, str]]:
    """Persist each head-backed row's rendered head and suggestion."""
    return {
        row["id"]: {
            "head_sha": str(row.get("head_sha") or ""),
            "suggested_disposition": str(row.get("suggested_disposition") or ""),
        }
        for row in prepared
        if row.get("head_sha")
    }


def _pr_link(row: dict[str, Any]) -> str:
    """Render the PR cell as a markdown link, or plain text when unsafe."""
    url = _safe_url(row.get("url"))
    text = _markdown_cell(row.get("pr"))
    return f"[{text}]({url})" if url else text


def _human_row_line(row: dict[str, Any]) -> str:
    """Render one human-decision backlog row."""
    return (
        f"| {_pr_link(row)} | "
        f"{_markdown_cell(row.get('blocker'))} | "
        f"{_markdown_cell(row.get('evidence'), 160)} | "
        f"{_markdown_cell(row.get('recommended_action'), 200)} | "
        f"{_markdown_cell(row.get('safe_default'), 160)} | "
        f"{_markdown_cell(row.get('owner'))} | "
        f"{row['first_seen']} | {row['expires']} | "
        f"{'OVERDUE' if row['overdue'] else ''} |"
    )


def _handoff_row_line(row: dict[str, Any]) -> str:
    """Render one Stage 2 handoff row (no expiry or status columns)."""
    return (
        f"| {_pr_link(row)} | "
        f"{_markdown_cell(row.get('blocker'))} | "
        f"{_markdown_cell(row.get('evidence'), 160)} | "
        f"{_markdown_cell(row.get('recommended_action'), 200)} | "
        f"{_markdown_cell(row.get('owner'))} | "
        f"{row['first_seen']} |"
    )


def _capped_row_lines(
    rows: Iterable[dict[str, Any]],
    render: Callable[[dict[str, Any]], str],
    used: int,
) -> tuple[list[str], int, int]:
    """Render rows while the table stays under _BACKLOG_TABLE_CHAR_CAP."""
    lines: list[str] = []
    omitted = 0
    for row in rows:
        line = render(row)
        if used + len(line) + 1 > _BACKLOG_TABLE_CHAR_CAP:
            omitted += 1
            continue
        used += len(line) + 1
        lines.append(line)
    return lines, used, omitted


def _append_handoff_table(table: list[str], prepared: list[dict[str, Any]]) -> None:
    """Append the Stage 2 handoffs section when non-human rows exist."""
    handoffs = [r for r in prepared if _is_handoff_row(r)]
    if not handoffs:
        return
    table.extend(
        [
            "",
            "Stage 2 handoffs (no human decision needed):",
            "",
            "| PR | Blocker | Evidence | Recommended action | Owner | First seen |",
            "| --- | --- | --- | --- | --- | --- |",
        ]
    )
    used = sum(len(line) + 1 for line in table)
    lines, _, omitted = _capped_row_lines(handoffs, _handoff_row_line, used)
    table.extend(lines)
    if omitted:
        table.append(f"| — | {omitted} rows omitted (body cap) | | | | |")


def backlog_issue_body(
    spec: _BacklogSpec,
    rows: list[dict[str, Any]],
) -> str:
    """Render the per-repository human decision backlog and durable state."""
    prepared, final_state, _ = _prepare_backlog_rows(spec, rows)
    updated = _iso(spec.now)
    if not prepared:
        content = f"No open items needing a human decision as of {updated}."
    else:
        table = [
            "| PR | Blocker | Evidence | Recommended action | Safe default | Owner | First seen | Expires | Status |",
            "| --- | --- | --- | --- | --- | --- | --- | --- | --- |",
        ]
        used = sum(len(line) + 1 for line in table)
        rows, used, omitted = _capped_row_lines(
            (r for r in prepared if not _is_handoff_row(r)), _human_row_line, used
        )
        table.extend(rows)
        if omitted:
            table.append(
                f"| — | {omitted} more rows omitted (body cap) | | | | | | | |"
            )
        _append_handoff_table(table, prepared)
        # Lazy import: decision_rows needs helpers defined above in this module.
        from pr_lifecycle_decision_rows import decision_lines

        table.extend(decision_lines(prepared, sum(len(line) + 1 for line in table)))
        content = "\n".join(table)
    return (
        f"{_BACKLOG_MARKER}\n"
        f"updated_at_utc: {updated}\n"
        f"open_items: {len(prepared)}\n"
        f"overdue_items: {sum(bool(row['overdue']) for row in prepared)}\n\n"
        f"{content}\n\n"
        f"<!-- pr-lifecycle-backlog-state "
        f"{json.dumps(final_state, sort_keys=True, separators=(',', ':'))} -->\n"
    )


def update_backlog_issue(
    repo: str,
    rows: list[dict[str, Any]],
    *,
    now: datetime,
    notify_overdue: bool = True,
) -> dict[str, Any]:
    """Refresh or create a per-repository human decision issue.

    Preserve first-seen state and comment on newly overdue rows. Return a
    result with action EDITED or CREATED, the rendered body, issue number
    (possibly None after creation), row count, notified keys, and step results.
    An empty backlog edits an existing issue; if absent, return NOOP_EMPTY
    with the repository and body without creating an issue.

    Pass ``notify_overdue=False`` to skip the @-mention overdue comments and
    leave them unrecorded, so they can still fire on a later enabled run.

    Raise OSError for failed commands or malformed listings, or if a newly
    created overdue issue has no returned URL. Process launch errors and
    timeouts propagate. Earlier GitHub mutations are not rolled back.
    """
    github_steps: list[dict[str, Any]] = []
    issue = _find_backlog_issue(_list_backlog_rows(repo))
    old_state = _previous_state(issue.get("body") if issue else None)
    prepared, state, overdue = _prepare_backlog_rows(
        _BacklogSpec(repo, old_state, now, record_overdue=notify_overdue), rows
    )
    if not prepared and issue is None:
        body = backlog_issue_body(_BacklogSpec(repo, old_state, now), rows)
        return {"action": "NOOP_EMPTY", "repository": repo, "body": body}
    work = _BacklogWork(
        repo=repo,
        rows=rows,
        old_state=old_state,
        state=state,
        overdue=overdue,
        prepared=prepared,
        now=now,
        github_steps=github_steps,
    )
    if issue is not None:
        return _edit_backlog_issue(work, issue)
    return _create_backlog_issue(work)


@dataclass(frozen=True)
class _BacklogWork:
    """Shared context for the edit/create backlog-issue paths."""

    repo: str
    rows: list[dict[str, Any]]
    old_state: dict[str, Any]
    state: dict[str, Any]
    overdue: list[dict[str, Any]]
    prepared: list[dict[str, Any]]
    now: datetime
    github_steps: list[dict[str, Any]]


def _edit_backlog_issue(work: _BacklogWork, issue: dict[str, Any]) -> dict[str, Any]:
    """Notify overdue rows and edit the existing backlog issue body."""
    issue_number = int(issue["number"])
    if work.overdue:
        _notify_overdue(work.repo, work.overdue, issue_number, work.github_steps)
    body = backlog_issue_body(
        _BacklogSpec(
            work.repo, work.state if work.overdue else work.old_state, work.now
        ),
        work.rows,
    )
    _gh_step(
        ["edit", str(issue_number), "--body", body],
        "edit",
        work.repo,
        work.github_steps,
    )
    return _backlog_result("EDITED", work, issue.get("number"), body)


def _notify_created_issue(
    work: _BacklogWork, match: re.Match[str] | None
) -> tuple[str, int]:
    """Notify overdue rows on a fresh issue; return (new body, issue number)."""
    if match is None:
        raise OSError("gh issue create did not return the new issue URL")
    issue_number = int(match.group(1))
    _notify_overdue(work.repo, work.overdue, issue_number, work.github_steps)
    body = backlog_issue_body(_BacklogSpec(work.repo, work.state, work.now), work.rows)
    _gh_step(
        ["edit", str(issue_number), "--body", body],
        "edit",
        work.repo,
        work.github_steps,
    )
    return body, issue_number


def _create_backlog_issue(work: _BacklogWork) -> dict[str, Any]:
    """Create the backlog issue and notify overdue rows on it when needed."""
    body = backlog_issue_body(
        _BacklogSpec(work.repo, work.old_state, work.now, False), work.rows
    )
    created = _gh_step(
        ["create", "--title", BACKLOG_ISSUE_TITLE, "--body", body],
        "create",
        work.repo,
        work.github_steps,
    )
    match = re.search(r"/issues/(\d+)\b", created.stdout or "")
    issue_number = int(match.group(1)) if match is not None else None
    if work.overdue:
        body, issue_number = _notify_created_issue(work, match)
    return _backlog_result("CREATED", work, issue_number, body)


def _raise_gh(prefix: str, result: subprocess.CompletedProcess[str]) -> None:
    """Raise OSError carrying the command prefix, rc, and bounded stderr."""
    stderr = (result.stderr or "").strip()[:200]
    raise OSError(f"{prefix} rc={result.returncode}: {stderr}")


def _gh_step(
    cmd: list[str], step: str, repo: str, steps: list[dict[str, Any]]
) -> subprocess.CompletedProcess[str]:
    """Run a mutating gh issue call, record its exit code, raise on failure."""
    result = _gh_issue(cmd, repo)
    steps.append({"step": step, "exit_code": result.returncode})
    if result.returncode != 0:
        _raise_gh("gh issue update failed", result)
    return result


def _notify_overdue(
    repo: str,
    overdue: list[dict[str, Any]],
    issue_number: int,
    github_steps: list[dict[str, Any]],
) -> None:
    """Post the overdue @-mention summary and record its step result.

    Comments before the notified-state persists so a failed comment never
    loses the notification; a later edit failure only risks a duplicate
    ping on the next run.
    """
    comment_body = (
        f"@abhimehro {len(overdue)} item(s) passed their decision deadline:\n"
        + "\n".join(
            f"- {_markdown_cell(row.get('url') or row.get('pr'))}: "
            f"{_markdown_cell(row.get('blocker'))} "
            f"(expires {row['expires']})"
            for row in overdue
        )
    )
    comment = _gh_issue(["comment", str(issue_number), "--body", comment_body], repo)
    github_steps.append({"step": "overdue_comment", "exit_code": comment.returncode})
    if comment.returncode != 0:
        _raise_gh("gh issue overdue comment failed", comment)


def _backlog_result(
    action: str, work: _BacklogWork, issue_number: Any, body: str
) -> dict[str, Any]:
    """Assemble the update_backlog_issue result payload."""
    return {
        "action": action,
        "repository": work.repo,
        "issue_number": issue_number,
        "row_count": len(work.prepared),
        "overdue_notified": [row["id"] for row in work.overdue],
        "body": body,
        "github_steps": work.github_steps,
    }
