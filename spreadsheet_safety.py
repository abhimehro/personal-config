"""Defenses against spreadsheet formula injection in exported tabular data."""

from __future__ import annotations

# SECURITY: Values starting with these characters may execute as formulas when a
# markdown/CSV table is opened in Excel, LibreOffice Calc, or Google Sheets
# (CWE-1236). Prefix with a single quote to force literal interpretation.
_FORMULA_PREFIX_CHARS = ("=", "+", "-", "@", "\t", "\r")


def escape_spreadsheet_formula(value: str) -> str:
    """Return *value* safe for spreadsheet cells sourced from untrusted text.

    PR titles, branch names, and author logins are attacker-influenceable via
    GitHub and must not be emitted into inventory tables without escaping.
    """
    if not value:
        return value
    if value[0] in _FORMULA_PREFIX_CHARS:
        return "'" + value
    return value
