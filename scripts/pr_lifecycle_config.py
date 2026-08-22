"""Configuration and checked-in Cursor export validation for the PR lifecycle."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from pr_identity import identity_policy_from_config
from pr_lifecycle_support import ROOT, require_fields, require_list, require_mapping


def validate_config(config: dict[str, Any]) -> None:
    legacy = {"merge_strategy", "auto_fix_enabled", "human_escalation_channel"}
    present = legacy & set(config)
    if present:
        raise ValueError(
            f"config: legacy lifecycle keys are prohibited: {sorted(present)}"
        )
    repos = require_list(config.get("repos"), "config.repos")
    if not repos:
        raise ValueError("config.repos: at least one repository is required")
    lifecycle = require_mapping(config.get("lifecycle"), "config.lifecycle")
    required = {
        "version",
        "source_of_truth",
        "schema",
        "validation_command",
        "cursor_dashboard_runtime",
        "policy_revision",
        "policy_inputs",
        "runtime_ledger",
        "routine_evidence_expiry_days",
        "no_op_or_supersession_cooldown_hours",
        "stale_close_cooldown_hours",
        "stage_caps",
        "stages",
    }
    require_fields(lifecycle, required, required, "config.lifecycle")
    require_fetched_ledger_command(lifecycle["validation_command"])
    validate_identity_classification(config)
    validate_policy_inputs(lifecycle["policy_inputs"])
    require_exact_stage_caps(lifecycle["stage_caps"])
    require_exact_stage_contract(lifecycle["stages"])


def require_fetched_ledger_command(command: Any) -> None:
    expected = (
        'python3 scripts/validate_pr_lifecycle_artifacts.py "$RUNTIME_LEDGER_PATH"'
    )
    if command != expected:
        raise ValueError(
            "config.lifecycle.validation_command: must require fetched runtime ledger path"
        )


def validate_identity_classification(config: dict[str, Any]) -> None:
    identity = require_mapping(
        config.get("identity_classification"), "config.identity_classification"
    )
    required = {
        "source",
        "ambiguous_identity",
        "title_branch_body_comment_inference",
        "revision",
        "required_independent_signals",
        "maintainer_token_logins",
        "branch_prefixes",
        "title_keywords",
        "body_markers",
        "bot_commit_email_suffixes",
    }
    require_fields(identity, required, required, "config.identity_classification")
    _validate_identity_source(identity)
    _validate_identity_ambiguous(identity)
    _validate_identity_inference(identity)
    policy = identity_policy_from_config(config)
    inputs = require_mapping(
        config["lifecycle"]["policy_inputs"], "config.lifecycle.policy_inputs"
    )
    _validate_identity_revision_match(policy, inputs)
    _validate_identity_signals(policy)


def _validate_identity_source(identity: dict[str, Any]) -> None:
    if identity["source"] != "github_api_with_token_authored_provenance":
        raise ValueError("config.identity_classification.source: unsupported policy")


def _validate_identity_ambiguous(identity: dict[str, Any]) -> None:
    if identity["ambiguous_identity"] != "HUMAN":
        raise ValueError(
            "config.identity_classification.ambiguous_identity: must be HUMAN"
        )


def _validate_identity_inference(identity: dict[str, Any]) -> None:
    inference = identity["title_branch_body_comment_inference"]
    if inference != "token_authored_provenance_only":
        raise ValueError(
            "config.identity_classification.title_branch_body_comment_inference: "
            "must be token_authored_provenance_only"
        )


def _validate_identity_revision_match(policy: Any, inputs: dict[str, Any]) -> None:
    if policy.revision != inputs["identity_classification_revision"]:
        raise ValueError(
            "config.identity_classification.revision: must match policy_inputs"
        )


def _validate_identity_signals(policy: Any) -> None:
    if policy.required_independent_signals < 2:
        raise ValueError(
            "config.identity_classification.required_independent_signals: must be >= 2"
        )


def validate_policy_inputs(value: Any) -> None:
    inputs = require_mapping(value, "config.lifecycle.policy_inputs")
    required = {
        "identity_classification_revision",
        "sensitive_path_taxonomy_revision",
        "permission_scope_revision",
        "required_check_source_revision",
        "merge_method_revision",
        "prompt_revision",
    }
    require_fields(inputs, required, required, "config.lifecycle.policy_inputs")


def require_exact_stage_caps(value: Any) -> None:
    caps = require_mapping(value, "config.lifecycle.stage_caps")
    expected = {
        "stage1_inventory": 50,
        "stage1_actions": 20,
        "stage2_salvage_candidates": 5,
        "stage3_reconciliation": 20,
        "stage3_decision_packets": 5,
        "stage3_completion_actions": 5,
    }
    if caps != expected:
        raise ValueError("config.lifecycle.stage_caps: differs from approved contract")


def require_exact_stage_contract(value: Any) -> None:
    stages = require_mapping(value, "config.lifecycle.stages")
    expected = {
        "stage1_review": {
            "schedule": "0 15 * * *",
            "concurrency": 1,
            "authority": "routine-approve-squash-merge-close",
        },
        "stage2_salvage": {
            "schedule": "0 17 * * *",
            "concurrency": 1,
            "authority": "draft-only-recovery",
        },
        "stage3_completion": {
            "schedule": "0 19 * * *",
            "concurrency": 1,
            "authority": "report-only-until-calibration-approved-then-bounded-nonsecurity-completion",
        },
    }
    if stages != expected:
        raise ValueError("config.lifecycle.stages: differs from approved contract")


def validate_bootstrap_pointer(pointer: dict[str, Any], config: dict[str, Any]) -> None:
    required = {"pointer_version", "pointer_kind", "runtime_ledger"}
    require_fields(pointer, required, required, "ledger pointer")
    validate_pointer_identity(pointer)
    runtime = require_mapping(
        pointer["runtime_ledger"], "ledger pointer.runtime_ledger"
    )
    validate_pointer_runtime_shape(runtime)
    expected = config["lifecycle"]["runtime_ledger"]
    validate_pointer_location(runtime, expected)
    validate_pointer_activation(runtime)
    validate_pointer_primitives(runtime, expected)


def validate_pointer_identity(pointer: dict[str, Any]) -> None:
    valid = pointer["pointer_version"] == "1.0"
    valid = valid and pointer["pointer_kind"] == "runtime_lifecycle_ledger"
    if not valid:
        raise ValueError("ledger pointer: unsupported version or kind")


def validate_pointer_runtime_shape(runtime: dict[str, Any]) -> None:
    fields = {
        "data_branch",
        "data_path",
        "schema_path",
        "activation_state",
        "selected_write_primitive",
        "allowed_write_primitives",
        "bootstrap_document",
    }
    require_fields(runtime, fields, fields, "ledger pointer.runtime_ledger")


def validate_pointer_location(
    runtime: dict[str, Any], expected: dict[str, Any]
) -> None:
    matches = runtime["data_branch"] == expected["data_branch"]
    matches = matches and runtime["data_path"] == expected["data_path"]
    if not matches:
        raise ValueError("ledger pointer: runtime location differs from config")


def validate_pointer_activation(runtime: dict[str, Any]) -> None:
    state = runtime["activation_state"]
    selected = runtime["selected_write_primitive"]
    allowed = set(runtime["allowed_write_primitives"])
    if state not in {"NOT_BOOTSTRAPPED", "ACTIVE"}:
        raise ValueError("ledger pointer: invalid activation state")
    if state == "NOT_BOOTSTRAPPED":
        if selected is not None:
            raise ValueError(
                "ledger pointer: inactive pointer must not select a primitive"
            )
    elif selected not in allowed:
        raise ValueError(
            "ledger pointer: active pointer selects an unsupported primitive"
        )


def validate_pointer_primitives(
    runtime: dict[str, Any], expected: dict[str, Any]
) -> None:
    if set(runtime["allowed_write_primitives"]) != set(
        expected["allowed_write_primitives"]
    ):
        raise ValueError("ledger pointer: allowed primitives differ from config")


def validate_exports_and_prompts(config: dict[str, Any]) -> None:
    expected = {
        "daily-pr-review.json": ("stage1_review", True, "daily-pr-review.md"),
        "daily-pr-salvage.json": ("stage2_salvage", False, "daily-pr-salvage.md"),
        "daily-pr-completion.calibration.json": (
            "stage3_completion",
            False,
            "daily-pr-completion.calibration.md",
        ),
        "daily-pr-completion.json": (
            "stage3_completion",
            True,
            "daily-pr-completion.md",
        ),
    }
    stages = config["lifecycle"]["stages"]
    directory = ROOT / "docs/cursor-automations/exports"
    prompt_dir = ROOT / "docs/cursor-automations/prompts"
    for export_name, (stage, allow_approve, prompt_name) in expected.items():
        path = directory / export_name
        data = json.loads(path.read_text(encoding="utf-8"))
        validate_export_shape(data, path, stages[stage]["schedule"], allow_approve)
        source = (prompt_dir / prompt_name).read_text(encoding="utf-8").strip() + "\n"
        if data["prompts"][0].get("prompt") != source:
            raise ValueError(f"{path}: prompt differs from source")
        validate_prompt(source, prompt_name)


def validate_export_shape(
    data: dict[str, Any], path: Path, schedule: str, allow_approve: bool
) -> None:
    fields = {
        "name",
        "triggers",
        "actions",
        "prompts",
        "model",
        "agentOptions",
        "memoryEnabled",
        "scope",
    }
    if set(data) != fields:
        raise ValueError(f"{path}: export fields differ from observed Cursor shape")
    validate_export_schedule(data, path, schedule)
    validate_export_memory(data, path)
    validate_export_approval(data, path, allow_approve)
    validate_export_actions(data, path)


def validate_export_schedule(data: dict[str, Any], path: Path, schedule: str) -> None:
    if data["triggers"][0]["cron"]["cron"] != schedule:
        raise ValueError(f"{path}: cron differs from lifecycle stage")


def validate_export_memory(data: dict[str, Any], path: Path) -> None:
    if data["memoryEnabled"] is not True:
        raise ValueError(f"{path}: memory must be enabled")


def validate_export_approval(
    data: dict[str, Any], path: Path, allow_approve: bool
) -> None:
    approvals = [
        action
        for action in data["actions"]
        if action.get("prComment", {}).get("allowApprove") is True
    ]
    if bool(approvals) != allow_approve:
        raise ValueError(f"{path}: approval authority differs from stage")


def validate_export_actions(data: dict[str, Any], path: Path) -> None:
    for action in require_list(data["actions"], f"{path}.actions"):
        validate_export_action(action, path)


def validate_export_action(action: dict[str, Any], path: Path) -> None:
    if "requestReviewers" in action:
        raise ValueError(f"{path}: reviewer requests are prohibited")
    kind = next(
        (candidate for candidate in ("mcp", "prComment") if candidate in action), None
    )
    validator = {
        "mcp": validate_mcp_action,
        "prComment": validate_pr_comment_action,
    }.get(kind)
    if validator is None:
        raise ValueError(f"{path}: unsupported action")
    validator(action, path)


def validate_mcp_action(action: dict[str, Any], path: Path) -> None:
    server = action["mcp"].get("server", {})
    if server.get("name") != "GitKraken" or server.get("id") != "5021":
        raise ValueError(f"{path}: export must preserve observed GitKraken connector")


def validate_pr_comment_action(action: dict[str, Any], path: Path) -> None:
    if "prComment" not in action:
        raise ValueError(f"{path}: unsupported action")


def validate_prompt(content: str, name: str) -> None:
    required = {
        "docs/automated-pr-lifecycle.md",
        "docs/pr-lifecycle-runtime-ledger.md",
        "Memory is enabled",
        "Dashboard-referenced MCP set",
        "ledger, run records, and lessons",
    }
    if any(marker not in content for marker in required):
        raise ValueError(f"{name}: missing runtime continuity marker")
