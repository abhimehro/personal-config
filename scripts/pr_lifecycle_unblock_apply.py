"""Bounded GitHub mutations for the PR lifecycle unblock stage.

Each selected action records per-step exit codes in github_steps; a nonzero
step other than the best-effort label creation lands in unconfirmed. Closes
are confirmed by re-reading PR state. Nothing here merges or deletes.
"""

from __future__ import annotations

import json
import subprocess
from typing import Any

_MUTATING_ACTIONS = {
    "CLOSE_STALE_LINEAGE",
    "CLOSE_SUPERSEDED",
    "UPDATE_BRANCH",
    "TRIGGER",
}


def _run_github_step(
    argv: list[str], step: str, *, run: Any = subprocess.run
) -> dict[str, Any]:
    """Run one GitHub command and return its exit code or process error type."""
    try:
        result = run(
            argv,
            check=False,
            capture_output=True,
            text=True,
            timeout=60,
        )
    except (OSError, subprocess.SubprocessError) as exc:
        return {"step": step, "exit_code": None, "error": type(exc).__name__}
    return {"step": step, "exit_code": result.returncode}


def _update_branch_step(
    repo: str, pr: str, action: dict[str, Any], *, run: Any
) -> dict[str, Any]:
    """Request a branch update pinned to the expected head SHA."""
    return _run_github_step(
        [
            "gh",
            "api",
            "-X",
            "PUT",
            f"repos/{repo}/pulls/{pr}/update-branch",
            "-f",
            f"expected_head_sha={action['expected_head_sha']}",
        ],
        "update_branch",
        run=run,
    )


def _trigger_step(
    repo: str, pr: str, action: dict[str, Any], *, run: Any
) -> dict[str, Any]:
    """Post the trigger comment body carried by the action."""
    return _run_github_step(
        [
            "gh",
            "pr",
            "comment",
            pr,
            "--repo",
            repo,
            "--body",
            str(action["body"]),
        ],
        "trigger_comment",
        run=run,
    )


def _confirm_close(repo: str, pr: str, *, run: Any) -> dict[str, Any]:
    """Re-read PR state after a close so the plan records confirmation."""
    try:
        result = run(
            ["gh", "pr", "view", pr, "--repo", repo, "--json", "state"],
            check=False,
            capture_output=True,
            text=True,
            timeout=60,
        )
    except (OSError, subprocess.SubprocessError) as exc:
        return {
            "step": "confirm",
            "exit_code": None,
            "error": type(exc).__name__,
        }
    read: dict[str, Any] = {"step": "confirm", "exit_code": result.returncode}
    if result.returncode == 0:
        try:
            read["state"] = json.loads(result.stdout).get("state")
        except (json.JSONDecodeError, AttributeError):
            read["state"] = None
    return read


def _close_pr_steps(
    repo: str, pr: str, action: dict[str, Any], *, run: Any
) -> list[dict[str, Any]]:
    """Run the label, close, confirm, then comment sequence for a close action.

    The explanatory comment posts only after the close is confirmed, so a
    failed close does not repeat the comment on every run.
    """
    steps = [
        _run_github_step(
            [
                "gh",
                "label",
                "create",
                "superseded",
                "--repo",
                repo,
                "--color",
                "cfd3d7",
                "--description",
                "Superseded by another PR (pr-lifecycle)",
            ],
            "ensure_label",
            run=run,
        ),
        _run_github_step(
            [
                "gh",
                "pr",
                "edit",
                pr,
                "--repo",
                repo,
                "--add-label",
                "superseded",
            ],
            "label",
            run=run,
        ),
        _run_github_step(
            ["gh", "pr", "close", pr, "--repo", repo],
            "close",
            run=run,
        ),
    ]
    steps.append(_confirm_close(repo, pr, run=run))
    if str(steps[-1].get("state") or "").upper() == "CLOSED":
        steps.append(
            _run_github_step(
                [
                    "gh",
                    "pr",
                    "comment",
                    pr,
                    "--repo",
                    repo,
                    "--body",
                    str(action["comment"]),
                ],
                "comment",
                run=run,
            )
        )
    return steps


def _apply_action(action: dict[str, Any], *, run: Any = subprocess.run) -> None:
    """Execute a selected GitHub mutation and attach step results to the action.

    Branch updates use the expected head SHA; closes are re-read for
    confirmation. Record failures in github_steps and unconfirmed.
    """
    steps = _steps_for_action(action, run=run)
    action["github_steps"] = steps
    action["unconfirmed"] = any(
        step.get("exit_code") != 0
        for step in steps
        if step.get("step") != "ensure_label"
    )
    if action["action"] in {"CLOSE_STALE_LINEAGE", "CLOSE_SUPERSEDED"}:
        confirm = next((step for step in steps if step["step"] == "confirm"), {})
        if str(confirm.get("state") or "").upper() != "CLOSED":
            action["unconfirmed"] = True


def _steps_for_action(
    action: dict[str, Any], *, run: Any = subprocess.run
) -> list[dict[str, Any]]:
    """Execute the action's GitHub commands and return their step results."""
    repo = str(action["repository"])
    pr = str(action["pr"])
    if action["action"] == "UPDATE_BRANCH":
        return [_update_branch_step(repo, pr, action, run=run)]
    if action["action"] == "TRIGGER":
        return [_trigger_step(repo, pr, action, run=run)]
    if action["action"] in {"CLOSE_STALE_LINEAGE", "CLOSE_SUPERSEDED"}:
        return _close_pr_steps(repo, pr, action, run=run)
    raise ValueError(f"unsupported action: {action['action']}")
