"""Render tickable disposition rows for the per-repo decision issue."""

from typing import Any

# Shared table/row helpers live here so issue_status can render decision rows
# without an import cycle (issue_status -> decision_rows, never the reverse).
_BACKLOG_TABLE_CHAR_CAP = 45_000


def _markdown_cell(value: object, limit: int = 300) -> str:
    """Bound cell text and neutralize pipes, comment markers, and mentions."""
    text = " ".join(str(value or "").replace("|", "\\|").split())
    text = text.replace("<!--", "&lt;!--").replace("-->", "--&gt;")
    text = text.replace("@", "@\u200b")
    return text[:limit]


def _is_handoff_row(row: dict[str, Any]) -> bool:
    """True for rows handed to a non-human owner (e.g. stage2 escalations)."""
    return row.get("owner") not in (None, "human")


__all__ = ["decision_lines"]


def _decision_row_line(row: dict[str, Any]) -> str:
    """Render one tickable disposition row."""
    return (
        f"- [ ] **{row['id']}** — suggested "
        f"`{_markdown_cell(row.get('suggested_disposition') or 'KEEP_OPEN')}` "
        f"· head `{_markdown_cell(str(row.get('head_sha') or '')[:7] or 'unknown')}`"
        f" · {_markdown_cell(row.get('blocker'))}"
    )


def _tickable(row: dict[str, Any]) -> bool:
    """Only head-backed, non-handoff rows get a checkbox."""
    return not _is_handoff_row(row) and bool(row.get("head_sha"))


def _fits(header: list[str], rows: list[str], line: str, used: int) -> bool:
    """True when the next row still fits the shared body budget."""
    return (
        used + sum(len(line_) + 1 for line_ in header + rows + [line])
        <= _BACKLOG_TABLE_CHAR_CAP
    )


def decision_lines(prepared: list[dict[str, Any]], used: int) -> list[str]:
    """Render tickable disposition rows inside the shared body budget."""
    header = [
        "",
        "Decisions — tick a checkbox to execute the suggested disposition. Ticks are",
        "honored only while the rendered head is still the PR's live head; every",
        "executed disposition is logged as a ledger event.",
        "",
    ]
    rows, omitted = [], 0
    for row in prepared:
        if not _tickable(row):
            continue
        line = _decision_row_line(row)
        if not _fits(header, rows, line, used):
            omitted += 1
            continue
        rows.append(line)
    if not rows:
        return []
    if omitted:
        rows.append(f"- {omitted} decision row(s) omitted (body cap)")
    return header + rows
