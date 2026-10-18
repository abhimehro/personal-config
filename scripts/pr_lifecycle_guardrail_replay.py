#!/usr/bin/env python3
"""Replay the guardrail classifier over a ledger snapshot. Read-only.

Prints, per rule, how many REVIEW_SECURITY / HOLD_CONTRACT / HOLD_EVIDENCE
items would become PASS_ROUTINE, with PR URLs. Also lists Jules Sentinel
persona PRs (title contains Sentinel, branch sentinel/ or jules/, including
the hyphen forms) with the old outcome and the outcome under the new rules.

Does not write the runtime ledger. A missing diff on an existing hold fails
closed and is counted under fetch_failed rather than as a move.
"""

from __future__ import annotations

import argparse
import json
import sys
import tempfile
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path
from typing import Any

import pr_lifecycle_guardrails as guardrails
import pr_lifecycle_ledger_cas as cas
from pr_lifecycle_yaml import load_yaml

_RULES = (
    "classification_without_sensitive_path",
    "jules_journal",
    "dependabot_routine",
)


def is_sentinel_persona(title: str, head_ref: str) -> bool:
    """Report a Jules Sentinel persona PR, which is not a security finding.

    The title must contain Sentinel. The branch must start with sentinel/ or
    jules/, or the hyphen forms this repo already treats as the same prefix.
    """
    if "sentinel" not in title.lower():
        return False
    ref = head_ref.lower()
    return ref.startswith(("sentinel/", "sentinel-", "jules/", "jules-"))


def _group_rule_moves(
    item: dict[str, Any], patch: dict[str, Any] | None
) -> tuple[str | None, dict[str, Any]]:
    """Return (rule, row) for the item if it qualifies for a rule move."""
    rule = guardrails.clearance_rule(item, patch)
    new_outcome = patch["guardrail_outcome"] if patch else item.get("guardrail_outcome")
    row = {
        "key": str(item.get("key") or ""),
        "url": item.get("url"),
        "repository": item.get("repository"),
        "pr": item.get("pr"),
        "old": item.get("guardrail_outcome"),
        "new": new_outcome,
    }
    if rule is not None:
        row["rule"] = rule
    return rule, row


def _audit_sentinel_persona(
    item: dict[str, Any],
    evidence: guardrails.GuardrailEvidence | None,
    patch: dict[str, Any] | None
) -> dict[str, Any] | None:
    """Return a Sentinel persona row if the item qualifies, else None."""
    if not (
        guardrails.is_sentinel_title_standin(item)
        or (
            evidence is not None
            and is_sentinel_persona(evidence.title or "", evidence.head_ref or "")
        )
    ):
        return None
    reasons = patch.get("sensitive_paths") if patch else item.get("sensitive_paths")
    return {
        "key": str(item.get("key") or ""),
        "url": item.get("url"),
        "repository": item.get("repository"),
        "pr": item.get("pr"),
        "old": item.get("guardrail_outcome"),
        "new": patch["guardrail_outcome"] if patch else item.get("guardrail_outcome"),
        "title": evidence.title if evidence else None,
        "head_ref": evidence.head_ref if evidence else None,
        "morning_reflagged": guardrails.is_sentinel_title_standin(item),
        "sensitive_paths": reasons or [],
    }


def replay_items(
    items: list[Any],
    evidence_by_key: dict[str, guardrails.GuardrailEvidence | None],
) -> dict[str, Any]:
    """Return rule-grouped clearance counts and a Sentinel audit without mutation."""
    grouped: dict[str, list[dict[str, Any]]] = {name: [] for name in _RULES}
    sentinel: list[dict[str, Any]] = []
    fetch_failed: list[str] = []
    for item in items:
        if not isinstance(item, dict):
            continue
        key = str(item.get("key") or "")
        evidence = evidence_by_key.get(key)
        if evidence is not None and evidence.diff_fetch_failed:
            fetch_failed.append(key)
        patch = guardrails.evaluate_item(item, evidence=evidence)
        rule, row = _group_rule_moves(item, patch)
        if rule is not None:
            grouped[rule].append(row)
        persona_row = _audit_sentinel_persona(item, evidence, patch)
        if persona_row is not None:
            sentinel.append(persona_row)
    unique = [row for rows in grouped.values() for row in rows]
    return {
        "rules": {
            name: {"count": len(rows), "items": rows} for name, rows in grouped.items()
        },
        "unique_move_count": len(unique),
        "fetch_failed": fetch_failed,
        "sentinel_persona": sentinel,
    }


def _advisory_patterns(config: dict[str, Any]) -> list[str]:
    """Return configured lifecycle.unblock advisory patterns as strings.

    Return an empty list when advisory_checks is missing, empty, or not a list.
    """
    unblock = (config.get("lifecycle") or {}).get("unblock") or {}
    patterns = unblock.get("advisory_checks") or []
    if not isinstance(patterns, list):
        return []
    return [str(pattern) for pattern in patterns]


def _should_fetch(item: dict[str, Any]) -> bool:
    """Return whether a nonterminal BOT item needs live replay evidence."""
    if item.get("lifecycle_state") == "TERMINAL":
        return False
    if item.get("author_type") != "BOT":
        return False
    if item.get("guardrail_outcome") in guardrails._CLEARABLE_HOLDS:
        return True
    if item.get("classification") == "SECURITY":
        return True
    return guardrails.needs_live_evidence(item)


def _load_config() -> dict[str, Any]:
    """Load the guardrail YAML configuration.

    Raise ValueError for an unreadable file, invalid YAML, or a non-mapping root.
    """
    loaded = load_yaml(guardrails.CONFIG_PATH)
    return loaded if isinstance(loaded, dict) else {}


def replay_ledger(ledger: dict[str, Any], *, fetch: bool) -> dict[str, Any]:
    """Return a replay report with ledger_revision without mutating the ledger.

    When fetch is True, read GitHub evidence for eligible BOT items, including
    diffs only when needed. Otherwise use ledger fields alone. Configuration
    is loaded in both modes; configuration and worker exceptions propagate.
    """
    config = _load_config()
    patterns = _advisory_patterns(config)
    evidence_by_key: dict[str, guardrails.GuardrailEvidence | None] = {}
    if fetch:
        to_fetch = [
            item
            for item in ledger.get("items") or []
            if isinstance(item, dict) and _should_fetch(item)
        ]
        with ThreadPoolExecutor(max_workers=8) as pool:
            futures = {
                str(item.get("key") or ""): pool.submit(
                    guardrails.fetch_guardrail_evidence,
                    item,
                    patterns,
                    include_diff=guardrails.needs_live_evidence(item),
                )
                for item in to_fetch
            }
            for key, future in futures.items():
                evidence_by_key[key] = future.result()
    items = ledger.get("items") or []
    report = replay_items(items, evidence_by_key)
    report["ledger_revision"] = ledger.get("ledger_revision")
    return report


def _format_rule_table(report: dict[str, Any]) -> list[str]:
    """Return markdown lines for the rule summary table."""
    lines = [
        f"Ledger revision: {report.get('ledger_revision')}",
        "",
        "| Rule | Moves to PASS_ROUTINE |",
        "| --- | ---: |",
    ]
    for name, payload in (report.get("rules") or {}).items():
        lines.append(f"| `{name}` | {payload.get('count', 0)} |")
    lines.append(f"| unique items | {report.get('unique_move_count', 0)} |")
    return lines


def _format_pr_urls(report: dict[str, Any]) -> list[str]:
    """Return markdown lines for PR URLs by rule."""
    lines = ["PR URLs"]
    for name, payload in (report.get("rules") or {}).items():
        lines.append(f"### {name}")
        for row in payload.get("items") or []:
            lines.append(f"- {row.get('url')} ({row.get('old')} → {row.get('new')})")
    return lines


def _format_sentinel_table(report: dict[str, Any]) -> list[str]:
    """Return markdown lines for the Sentinel persona table."""
    lines = [
        "",
        "Sentinel persona PRs",
        "",
        "| PR | Morning Re-flagged | Old | New | Why it stays held |",


def main(argv: list[str] | None = None) -> int:
    """Print a Markdown or JSON replay report; return zero on success.

    argv defaults to process arguments. --ledger selects a local snapshot;
    otherwise preflight fetches the runtime ledger. --no-fetch skips per-PR
    evidence requests but does not skip that ledger fetch.

    A non-mapping ledger raises ArtifactValidationError from load_yaml. Other
    YAML loading, preflight, and replay errors also propagate; argparse may
    raise SystemExit.
    """
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--ledger",
        type=Path,
        help="local ledger YAML (read-only). Default: fetch the runtime ledger",
    )
    parser.add_argument(
        "--no-fetch",
        action="store_true",
        help="do not call GitHub; use only fields already on the ledger",
    )
    parser.add_argument("--json", action="store_true")
    args = parser.parse_args(argv)
    if args.ledger is not None:
        ledger = load_yaml(args.ledger)
    else:
        with tempfile.TemporaryDirectory(prefix="pr-lifecycle-replay-") as tmp:
            path = Path(tmp) / "ledger.yaml"
            cas.run_preflight(path)
            ledger = load_yaml(path)
    if not isinstance(ledger, dict):
        print("PR_LIFECYCLE_REPLAY_ERROR: ledger_not_mapping", file=sys.stderr)
        return 1
    report = replay_ledger(ledger, fetch=not args.no_fetch)
    if args.json:
        print(json.dumps(report, indent=2, sort_keys=True))
    else:
        print(_format_report(report))
    return 0


def _format_sentinel_row(row: dict[str, Any]) -> str:
    """Return a markdown table row for a Sentinel persona PR."""
    repo = row.get("repository", "")
    number = row.get("pr", "")
    reflagged = "yes" if row.get("morning_reflagged") else "no"
    held = (
        ", ".join(row.get("sensitive_paths") or [])
        or "empty changed_paths (fail-closed)"
    )
    if row.get("new") == "PASS_ROUTINE":
        held = "—"
    return (
        f"| {repo}#{number} | {reflagged} | {row.get('old')} | "
        f"{row.get('new')} | {held} |"
    )


def _format_sentinel_table(report: dict[str, Any]) -> list[str]:
    """Return markdown lines for the Sentinel persona table."""
    lines = [
        "",
        "Sentinel persona PRs",
        "",
        "| PR | Morning Re-flagged | Old | New | Why it stays held |",
        "| --- | :---: | --- | --- | --- |",
    ]
    for row in report.get("sentinel_persona") or []:
        lines.append(_format_sentinel_row(row))
    return lines


def _format_report(report: dict[str, Any]) -> str:
    """Render the replay as markdown for a PR body."""
    lines = []
    lines.extend(_format_rule_table(report))
    lines.append("")
    lines.extend(_format_pr_urls(report))
    failed = report.get("fetch_failed") or []
    lines.append("")
    lines.append(f"Diff fetch failed (kept held): {len(failed)}")
    lines.extend(_format_sentinel_table(report))
    return "\n".join(lines) + "\n"


if __name__ == "__main__":
    raise SystemExit(main())
