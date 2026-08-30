#!/usr/bin/env python3
"""Detect Stage 2 starvation and summarize salvage-eligible ledger stock.

Read a fetched runtime ledger (never the main-branch pointer). Exit 2 when
Stage 2 would empty-intake while salvage-eligible BOT items remain. This is
observability for PR Desk and CI; it does not CAS-write, launch stages, or
merge PRs.

Salvage-eligible matches the lifecycle contract: BOT, nonterminal, not
REVIEW_SECURITY, sticky paths empty or only generated_output, not
HOLD_PLATFORM / HOLD_CANONICAL / PASS_ROUTINE / CLOSE_NONSECURITY_NOOP, and a
mechanical next_action (unique-source draft, wrap, lint, import, conflict
markers, DIRTY unique remaining). Lockfile/workflow/auth/secrets stay out.
"""

from __future__ import annotations

import argparse
import json
import re
import sys
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any

SCRIPT_DIR = Path(__file__).resolve().parent
if str(SCRIPT_DIR) not in sys.path:
    sys.path.insert(0, str(SCRIPT_DIR))

from pr_lifecycle_yaml import load_yaml  # noqa: E402

STICKY_SENSITIVE_PATHS = frozenset(
    {
        "lockfiles_and_major_dependencies",
        "workflows_and_permissions",
        "secrets",
        "authentication_and_authorization",
        "deployment_and_infrastructure",
        "security_configuration",
        "database_migrations",
        "network_browser_origins",
        "shell_execution",
        "file_read_write_boundaries",
        "public_api_contracts",
        "destructive_data_actions",
    }
)
NON_SALVAGE_OUTCOMES = frozenset(
    {
        "REVIEW_SECURITY",
        "HOLD_PLATFORM",
        "HOLD_CANONICAL",
        "PASS_ROUTINE",
        "CLOSE_NONSECURITY_NOOP",
        "ANALYSIS_ERROR",
        "NOT_RUN",
    }
)
MECHANICAL_NEXT_ACTION = re.compile(
    r"recover unique source|focused draft|conflict.?marker|"
    r"wrap (source|export)|TYPE_CHECKING|unique remaining|DIRTY",
    re.IGNORECASE,
)
MAJOR_DEP_BLOCK = re.compile(
    r"major-?dep|lockfile|pandas 3|opencv|workflow pin|uv\.lock",
    re.IGNORECASE,
)


@dataclass(frozen=True)
class PipelineHealth:
    ledger_revision: int
    stage2_work_item_count: int
    stage2_owned_item_count: int
    salvage_eligible_count: int
    salvage_eligible_keys: tuple[str, ...]
    starvation: bool
    reason: str


def is_salvage_eligible(item: dict[str, Any]) -> bool:
    """Return True when a ledger item should feed a complete Stage 2 work item."""
    if item.get("author_type") != "BOT":
        return False
    if item.get("lifecycle_state") == "TERMINAL":
        return False
    if item.get("current_owner") == "stage2":
        return False
    outcome = item.get("guardrail_outcome") or ""
    if outcome in NON_SALVAGE_OUTCOMES:
        return False
    sticky = set(item.get("sensitive_paths") or []) - {"generated_output"}
    if sticky:
        return False
    next_action = item.get("next_action") or ""
    if MAJOR_DEP_BLOCK.search(next_action) and "Recover unique source" not in (
        next_action
    ):
        return False
    if outcome not in {"HOLD_CONTRACT", "HOLD_EVIDENCE"}:
        return False
    return bool(MECHANICAL_NEXT_ACTION.search(next_action))


def summarize(ledger: dict[str, Any]) -> PipelineHealth:
    """Build a starvation report from a validated-shape runtime ledger dict."""
    items = list(ledger.get("items") or [])
    work_items = list(ledger.get("stage2_work_items") or [])
    owned = [
        item
        for item in items
        if item.get("current_owner") == "stage2"
        or item.get("lifecycle_state") in {"STAGE2_QUEUED", "STAGE2_ACTIVE"}
    ]
    eligible = [item for item in items if is_salvage_eligible(item)]
    queued = len(work_items) + len(owned)
    starvation = queued == 0 and len(eligible) > 0
    if starvation:
        reason = (
            "Stage 2 EMPTY_INTAKE while salvage-eligible > 0 "
            f"({len(eligible)} items)"
        )
    elif queued == 0:
        reason = "Stage 2 empty intake with zero salvage-eligible remainder"
    else:
        reason = "Stage 2 has queued work"
    revision = int(ledger.get("ledger_revision") or 0)
    keys = tuple(str(item.get("key") or "") for item in eligible)
    return PipelineHealth(
        ledger_revision=revision,
        stage2_work_item_count=len(work_items),
        stage2_owned_item_count=len(owned),
        salvage_eligible_count=len(eligible),
        salvage_eligible_keys=keys,
        starvation=starvation,
        reason=reason,
    )


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "runtime_ledger",
        type=Path,
        help="fetched runtime ledger from automation/pr-lifecycle-ledger",
    )
    parser.add_argument(
        "--json",
        action="store_true",
        help="print the health report as JSON",
    )
    args = parser.parse_args()
    pointer = args.runtime_ledger.resolve()
    if pointer.name == "pr-lifecycle-ledger.yaml" and "tasks" in pointer.parts:
        print(
            "PR_LIFECYCLE_HEALTH: refusing main-branch pointer "
            "(fetch automation/pr-lifecycle-ledger)",
            file=sys.stderr,
        )
        return 1
    try:
        ledger = load_yaml(args.runtime_ledger)
    except (OSError, ValueError, KeyError) as exc:
        print(f"PR_LIFECYCLE_HEALTH_ERROR: {exc}", file=sys.stderr)
        return 1
    report = summarize(ledger)
    payload = asdict(report)
    if args.json:
        print(json.dumps(payload, indent=2))
    else:
        print(f"ledger_revision={report.ledger_revision}")
        print(f"stage2_work_items={report.stage2_work_item_count}")
        print(f"stage2_owned_items={report.stage2_owned_item_count}")
        print(f"salvage_eligible={report.salvage_eligible_count}")
        print(f"starvation={str(report.starvation).lower()}")
        print(f"reason={report.reason}")
        for key in report.salvage_eligible_keys:
            print(f"eligible_key={key}")
    return 2 if report.starvation else 0


if __name__ == "__main__":
    raise SystemExit(main())
