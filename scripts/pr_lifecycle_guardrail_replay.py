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


def replay_items(
    items: list[Any],
    evidence_by_key: dict[str, guardrails.GuardrailEvidence | None],
) -> dict[str, Any]:
    """Return rule-grouped clearance counts and a Sentinel audit without mutation.

    Look up optional evidence by item key and skip non-mapping entries. Include
    old/new outcomes and PR URLs for moves from clearable holds to PASS_ROUTINE,
    keys whose evidence reports a failed fetch, and Sentinel persona rows.
    No evidence is fetched here; missing entries use path-only evaluation.
    """
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
        rule = guardrails.clearance_rule(item, patch)
        new_outcome = (
            patch.get("guardrail_outcome", item.get("guardrail_outcome"))
            if patch
            else item.get("guardrail_outcome")
        )
        row = {
            "key": key,
            "url": item.get("url"),
            "repository": item.get("repository"),
            "pr": item.get("pr"),
            "old": item.get("guardrail_outcome"),
            "new": new_outcome,
        }
        if rule is not None:
            row["rule"] = rule
            grouped[rule].append(row)
        if guardrails.is_sentinel_title_standin(item) or (
            evidence is not None
            and is_sentinel_persona(evidence.title or "", evidence.head_ref or "")
        ):
            reasons = (
                patch.get("sensitive_paths") if patch else item.get("sensitive_paths")
            )
            sentinel.append(
                {
                    **row,
                    "title": evidence.title if evidence else None,
                    "head_ref": evidence.head_ref if evidence else None,
                    "morning_reflagged": guardrails.is_sentinel_title_standin(item),
                    "sensitive_paths": reasons or [],
                }
            )
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


def _format_report(report: dict[str, Any]) -> str:
    """Render the replay as markdown for a PR body."""
    lines = [
        f"Ledger revision: {report.get('ledger_revision')}",
        "",
        "| Rule | Moves to PASS_ROUTINE |",
        "| --- | ---: |",
    ]
    for name, payload in (report.get("rules") or {}).items():
        lines.append(f"| `{name}` | {payload.get('count', 0)} |")
    lines.append(f"| unique items | {report.get('unique_move_count', 0)} |")
    lines.append("")
    lines.append("PR URLs")
    for name, payload in (report.get("rules") or {}).items():
        lines.append(f"### {name}")
        for row in payload.get("items") or []:
            lines.append(f"- {row.get('url')} ({row.get('old')} → {row.get('new')})")
    failed = report.get("fetch_failed") or []
    lines.append("")
    lines.append(f"Diff fetch failed (kept held): {len(failed)}")
    lines.append("")
    lines.append("Sentinel persona PRs")
    lines.append("")
    lines.append("| PR | Morning Re-flagged | Old | New | Why it stays held |")
    lines.append("| --- | :---: | --- | --- | --- |")
    for row in report.get("sentinel_persona") or []:
        repo = row.get("repository")
        number = row.get("pr")
        reflagged = "yes" if row.get("morning_reflagged") else "no"
        held = (
            ", ".join(row.get("sensitive_paths") or [])
            or "empty changed_paths (fail-closed)"
        )
        if row.get("new") == "PASS_ROUTINE":
            held = "—"
        lines.append(
            f"| {repo}#{number} | {reflagged} | {row.get('old')} | {row.get('new')} | {held} |"
        )
    return "\n".join(lines) + "\n"


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


if __name__ == "__main__":
    raise SystemExit(main())
