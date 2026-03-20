#!/usr/bin/env python3
from __future__ import annotations

import argparse

from repository_automation_common import enforce_result, load_config
from repository_automation_tasks import (
    run_backlog_manager,
    run_daily_status_report,
    run_performance_optimizer,
    run_quality_assurance,
    run_weekly_retrospective,
    run_workflow_updater,
)

TASK_RUNNERS = {
    "workflow-updater": run_workflow_updater,
    "performance-optimizer": run_performance_optimizer,
    "quality-assurance": run_quality_assurance,
    "backlog-manager": run_backlog_manager,
    "daily-status-report": run_daily_status_report,
    "weekly-retrospective": run_weekly_retrospective,
}


def main() -> int:
    parser = argparse.ArgumentParser(description="Consolidated repository automation runner")
    parser.add_argument("task")
    parser.add_argument("result_path", nargs="?")
    args = parser.parse_args()

    if args.task == "enforce":
        if not args.result_path:
            print("enforce requires a result path")
            return 1
        return enforce_result(args.result_path)

    runner = TASK_RUNNERS.get(args.task)
    if runner is None:
        print(f"Unknown task: {args.task}")
        return 1

    runner(load_config())
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
