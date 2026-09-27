#!/usr/bin/env python3
"""Stage runner preflight: print exact action plan + allowed commands.

``--stage 1|2|3`` emits a JSON plan and appends a JSONL run record under
``/tmp/pr-lifecycle/<run>.jsonl``. Updates ``status.json`` on the ledger
branch when ``--write-status`` is set. Classifies failures as TRANSIENT_RETRY
vs LOGIC_STOP.

``--status`` refreshes the pinned "PR pipeline status" GitHub issue.

Calibration stays disabled. Stage 2 never merges. Stage 3 re-reads predicates.
"""

from __future__ import annotations

import argparse
import importlib.util
import json
import logging
import sys
import tempfile
import uuid
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

SCRIPT_DIR = Path(__file__).resolve().parent
if str(SCRIPT_DIR) not in sys.path:
    sys.path.insert(0, str(SCRIPT_DIR))

# Fail fast with an install hint instead of a deep ModuleNotFoundError when
# the interpreter lacks requirements.txt (e.g. PEP 668 Homebrew python3).
_MISSING_DEPS = [
    package
    for module, package in (("yaml", "pyyaml"), ("jsonschema", "jsonschema"))
    if importlib.util.find_spec(module) is None
]
if _MISSING_DEPS:
    print(
        "PR_LIFECYCLE_RUN_ERROR: missing Python dependencies: "
        + ", ".join(_MISSING_DEPS)
        + f" (interpreter: {sys.executable}). Install requirements.txt, e.g. "
        "`python3 -m pip install -r requirements.txt`, or run via "
        "`uv run --with-requirements requirements.txt python3 "
        "scripts/pr_lifecycle_run.py ...`",
        file=sys.stderr,
    )
    raise SystemExit(2)

# pylint: disable=wrong-import-position
import pr_lifecycle_feed as feed_mod  # noqa: F401
import pr_lifecycle_ledger_cas as cas
import pr_lifecycle_pipeline_health as health
import pr_lifecycle_reconcile as reconcile_mod  # noqa: F401
from pr_lifecycle_config import validate_config
from pr_lifecycle_issue_status import issue_body as _issue_body  # noqa: F401
from pr_lifecycle_issue_status import update_pinned_issue
from pr_lifecycle_reselect_signals import SignalsResult, produce_reselect_signals
from pr_lifecycle_stage_plan import build_stage_plan

# Re-exports for tests that call run.plan_*/run._issue_body. Patching these
# names has no effect on the planner — it resolves them inside
# pr_lifecycle_stage_plan / pr_lifecycle_issue_status globals; patch there.
from pr_lifecycle_stage_plan import plan_stage2_enqueues  # noqa: F401
from pr_lifecycle_stage_plan import plan_stage3_mechanical_handoffs  # noqa: F401
from pr_lifecycle_support import ROOT
from pr_lifecycle_yaml import load_yaml

LOGGER = logging.getLogger(__name__)
LOG_DIR = Path(tempfile.gettempdir()) / "pr-lifecycle"
STATUS_PATH_ON_BRANCH = "status.json"


def _utc_now() -> datetime:
    """Return the current timezone-aware UTC time."""
    return datetime.now(timezone.utc)


def _run_id() -> str:
    """Generate a unique timestamped lifecycle run identifier."""
    stamp = _utc_now().strftime("%Y%m%dT%H%M%SZ")
    return f"{stamp}-{uuid.uuid4().hex[:8]}"


def _append_jsonl(path: Path, record: dict[str, Any]) -> None:
    """Append one JSON record to a JSONL file, creating parents as needed."""
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("a", encoding="utf-8") as handle:
        handle.write(json.dumps(record, sort_keys=True) + "\n")


def write_status_doc(plan: dict[str, Any], run_id: str) -> dict[str, Any]:
    """Build the compact status document for a stage plan."""
    doc = {
        "updated_at_utc": _utc_now().strftime("%Y-%m-%dT%H:%M:%SZ"),
        "run_id": run_id,
        "stage": plan.get("stage"),
        "ledger_revision": plan.get("ledger_revision"),
        "reason": plan.get("reason"),
        "stop_class": plan.get("stop_class"),
        "pipeline_health": plan.get("pipeline_health"),
        "signals_status": plan.get("signals_status"),
        "action_count": len(plan.get("actions") or []),
        "calibration_enabled": False,
    }
    if plan.get("signals_status") in {"DEGRADED", "PARTIAL"}:
        doc["condition"] = "SIGNALS_DEGRADED"
    if plan.get("signals_error"):
        doc["signals_error"] = plan["signals_error"]
    return doc


def _live_signals_result(
    ledger: dict[str, Any], enabled: bool
) -> tuple[SignalsResult, str | None]:
    """Fetch live signals fail-open; return (result, error_type_or_None).

    A producer exception degrades to empty signals with the exception type
    logged (never the message, which can echo gh output or tokens).
    """
    if not enabled:
        return SignalsResult(signals=health.ReselectSignals(), status="SKIPPED"), None
    try:
        return produce_reselect_signals(ledger), None
    except Exception as exc:  # pylint: disable=broad-exception-caught
        name = type(exc).__name__
        LOGGER.warning("PR_LIFECYCLE_RUN_WARNING: live signals DEGRADED (%s)", name)
        return (
            SignalsResult(signals=health.ReselectSignals(), status="DEGRADED"),
            name,
        )


def _attach_signal_fields(
    plan: dict[str, Any], result: SignalsResult, signals_error: str | None
) -> None:
    plan["signals_status"] = result.status
    plan["signals_queried"] = result.queried_count
    plan["signals_base_enriched"] = result.base_enriched_count
    plan["signals_failed_keys"] = list(result.failed_keys)
    plan["signals_truncated_keys"] = list(result.truncated_keys)
    plan["signals_elapsed_s"] = result.elapsed_s
    if signals_error:
        plan["signals_error"] = signals_error


def run_stage(
    stage: int,
    *,
    dry_run: bool,
    write_status: bool,
    no_live_signals: bool = False,
) -> int:
    """Fetch the ledger, emit and log a plan, and optionally write local status.

    Query live signals for Stages 1/3 unless no_live_signals is set. Producer
    exceptions degrade to ledger fallbacks. dry_run only labels the plan:
    reads and local writes still occur, and proposed actions are never applied.
    Append run records under LOG_DIR and, with write_status, replace its
    status.json mirror.

    Return 0 for a plan without LOGIC_STOP, 2 for LOGIC_STOP, or 1 for caught
    preflight/planning OSError, TypeError, ValueError, or KeyError failures.
    OSError failures are classified TRANSIENT_RETRY; other caught failures
    are LOGIC_STOP. Initial config loading/validation errors and local output
    I/O errors propagate, as do exceptions outside those caught classes.
    """
    config = load_yaml(ROOT / "tasks/pr-review-agent.config.yaml")
    validate_config(config)
    run_id = _run_id()
    log_path = LOG_DIR / f"{run_id}.jsonl"
    try:
        with tempfile.TemporaryDirectory(prefix="pr-lifecycle-run-") as tmp:
            out = Path(tmp) / "ledger.yaml"
            fetch = cas.run_preflight(out)
            ledger = load_yaml(Path(fetch["ledger_path"]))

            signals_result, signals_error = _live_signals_result(
                ledger, enabled=stage in (1, 3) and not no_live_signals
            )
            plan = build_stage_plan(
                stage, ledger, config, signals_result=signals_result
            )
            _attach_signal_fields(plan, signals_result, signals_error)
    except (OSError, TypeError, ValueError, KeyError, json.JSONDecodeError) as exc:
        # OSError covers fetch/service failures (recoverable); data-shape and
        # validation failures are repo-owned and cannot heal by retrying.
        stop_class = "TRANSIENT_RETRY" if isinstance(exc, OSError) else "LOGIC_STOP"
        record = {
            "run_id": run_id,
            "stage": stage,
            "stop_class": stop_class,
            "error": type(exc).__name__,
            "at_utc": _utc_now().strftime("%Y-%m-%dT%H:%M:%SZ"),
        }
        _append_jsonl(log_path, record)
        print(json.dumps(record, indent=2, sort_keys=True))
        return 1

    plan["run_id"] = run_id
    plan["dry_run"] = dry_run
    plan["log_path"] = str(log_path)
    _append_jsonl(log_path, {"event": "plan", **plan})
    print(json.dumps(plan, indent=2, sort_keys=True))

    if write_status:
        status = write_status_doc(plan, run_id)
        # Local mirror for agents; live branch update is a Stage ops concern.
        local_status = LOG_DIR / STATUS_PATH_ON_BRANCH
        local_status.parent.mkdir(parents=True, exist_ok=True)
        local_status.write_text(json.dumps(status, indent=2) + "\n", encoding="utf-8")
        _append_jsonl(log_path, {"event": "status", **status})

    if plan.get("stop_class") == "LOGIC_STOP":
        return 2
    return 0


def build_parser() -> argparse.ArgumentParser:
    """Build the lifecycle stage-runner command-line parser."""
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--stage", type=int, choices=[1, 2, 3], help="Stage")
    parser.add_argument(
        "--dry-run", action="store_true", default=True, help="Print plan only"
    )
    parser.add_argument(
        "--write-status",
        action="store_true",
        help="Write /tmp/pr-lifecycle/status.json for this run",
    )
    parser.add_argument(
        "--no-live-signals",
        action="store_true",
        help="Skip live GitHub signals fetch; use ledger fallbacks (status SKIPPED)",
    )
    parser.add_argument(
        "--status", action="store_true", help="Update pinned status issue"
    )
    return parser


def main(argv: list[str] | None = None) -> int:
    """Run a stage preflight or refresh the pinned status issue.

    Parse argv, defaulting to process arguments. --status takes precedence
    over --stage: create or update the GitHub issue, print status JSON, and
    return 0. Otherwise delegate planning and local output to run_stage and
    return its exit code (0, 1, or 2).

    Return 1 for a missing stage or caught OSError, TypeError, ValueError, or
    KeyError during execution. Other exceptions propagate; argument parsing
    raises SystemExit for help or invalid arguments.
    """
    args = build_parser().parse_args(argv)
    try:
        if args.status:
            status = {
                "updated_at_utc": _utc_now().strftime("%Y-%m-%dT%H:%M:%SZ"),
                "run_id": _run_id(),
                "stage": None,
                "reason": "manual --status refresh",
                "signals_status": "SKIPPED",
                "calibration_enabled": False,
            }
            update_pinned_issue(status)
            print(json.dumps(status, indent=2, sort_keys=True))
            return 0
        if args.stage is None:
            print("PR_LIFECYCLE_RUN_ERROR: --stage is required", file=sys.stderr)
            return 1
        return run_stage(
            args.stage,
            dry_run=args.dry_run,
            write_status=args.write_status,
            no_live_signals=args.no_live_signals,
        )
    except (OSError, TypeError, ValueError, KeyError, json.JSONDecodeError) as exc:
        print(f"PR_LIFECYCLE_RUN_ERROR: {type(exc).__name__}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
