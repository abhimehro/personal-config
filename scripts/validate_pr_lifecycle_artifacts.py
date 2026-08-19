#!/usr/bin/env python3
"""Fail-closed validation for the repository-native PR lifecycle artifacts.

This verifier intentionally does not execute a PR head, call GitHub, or mutate
state. It rejects duplicate YAML mapping keys, unsupported fields, malformed
identity/anchor records, invalid lifecycle transitions, and mismatched Cursor
export authority. The Cursor Dashboard remains a separately applied runtime
copy; this tool validates the reviewed source artifacts only.
"""

from __future__ import annotations

import argparse
import json
import re
import sys
from pathlib import Path
from typing import Any

import yaml

ROOT = Path(__file__).resolve().parents[1]
KEY_RE = re.compile(r"^[A-Za-z0-9_.-]+/[A-Za-z0-9_.-]+#[1-9][0-9]*@[0-9a-f]{40}$")
SHA_RE = re.compile(r"^[0-9a-f]{40}$")
UTC_RE = re.compile(r".+Z$")
URL_RE = re.compile(r"^https://")
ALLOWED_OUTCOMES = {"PASS_ROUTINE", "REVIEW_SECURITY", "HOLD_CONTRACT", "HOLD_EVIDENCE", "HOLD_PLATFORM", "HOLD_CANONICAL", "CLOSE_NONSECURITY_NOOP", "ANALYSIS_ERROR", "NOT_RUN"}
TERMINAL_DISPOSITIONS = {"MERGED_ROUTINE", "MERGED_BOUNDED_COMPLETION", "CLOSED_NOOP", "CLOSED_DUPLICATE", "CLOSED_STALE", "CLOSED_SUPERSEDED", "HUMAN_REJECTED", "HUMAN_DEFERRED"}
ITEM_FIELDS = {"key", "repository", "pr", "url", "base_sha", "head_sha", "author", "author_type", "classification", "risk_class", "sensitive_paths", "guardrail_outcome", "lifecycle_state", "terminal_disposition", "current_owner", "next_owner", "safe_default", "next_action", "evidence_urls", "changed_paths", "attempts", "handoffs", "revision", "updated_at_utc"}
ITEM_REQUIRED = ITEM_FIELDS - {"terminal_disposition"}
STATE_OWNERS = {
    "STAGE1_INTAKE": "stage1",
    "STAGE2_QUEUED": "stage2",
    "STAGE2_ACTIVE": "stage2",
    "STAGE3_RECONCILIATION": "stage3",
    "WAITING_HUMAN": "human",
    "TERMINAL": "none",
}


class UniqueKeyLoader(yaml.SafeLoader):
    """PyYAML loader that rejects duplicate mapping keys instead of overwriting."""


def _construct_mapping(loader: UniqueKeyLoader, node: yaml.MappingNode, deep: bool = False) -> dict[Any, Any]:
    mapping: dict[Any, Any] = {}
    for key_node, value_node in node.value:
        key = loader.construct_object(key_node, deep=deep)
        if key in mapping:
            raise ValueError(f"duplicate YAML key: {key!r}")
        mapping[key] = loader.construct_object(value_node, deep=deep)
    return mapping


UniqueKeyLoader.add_constructor(yaml.resolver.BaseResolver.DEFAULT_MAPPING_TAG, _construct_mapping)


def _load_yaml(path: Path) -> dict[str, Any]:
    try:
        data = yaml.load(path.read_text(encoding="utf-8"), Loader=UniqueKeyLoader)
    except (OSError, yaml.YAMLError, ValueError) as exc:
        raise ValueError(f"{path}: invalid YAML: {exc}") from exc
    if not isinstance(data, dict):
        raise ValueError(f"{path}: root must be a mapping")
    return data


def _require_mapping(value: Any, label: str) -> dict[str, Any]:
    if not isinstance(value, dict):
        raise ValueError(f"{label}: expected mapping")
    return value


def _require_list(value: Any, label: str) -> list[Any]:
    if not isinstance(value, list):
        raise ValueError(f"{label}: expected list")
    return value


def _require_fields(value: dict[str, Any], allowed: set[str], required: set[str], label: str) -> None:
    unknown = set(value) - allowed
    missing = required - set(value)
    if unknown:
        raise ValueError(f"{label}: unsupported fields: {sorted(unknown)}")
    if missing:
        raise ValueError(f"{label}: missing required fields: {sorted(missing)}")


def _require_utc(value: Any, label: str) -> None:
    if not isinstance(value, str) or not UTC_RE.fullmatch(value):
        raise ValueError(f"{label}: expected UTC timestamp ending in Z")


def _validate_item(item: Any, seen_keys: set[str]) -> None:
    value = _require_mapping(item, "ledger item")
    _require_fields(value, ITEM_FIELDS, ITEM_REQUIRED, "ledger item")
    key = value["key"]
    if not isinstance(key, str) or not KEY_RE.fullmatch(key):
        raise ValueError("ledger item: invalid key")
    if key in seen_keys:
        raise ValueError(f"ledger item: duplicate key {key}")
    seen_keys.add(key)
    if not isinstance(value["repository"], str) or not key.startswith(f"{value['repository']}#{value['pr']}@"):
        raise ValueError(f"ledger item {key}: key must match repository, PR, and head SHA")
    if not isinstance(value["head_sha"], str) or not key.endswith(value["head_sha"]) or not SHA_RE.fullmatch(value["head_sha"]):
        raise ValueError(f"ledger item {key}: key/head SHA mismatch")
    if not isinstance(value["base_sha"], str) or not SHA_RE.fullmatch(value["base_sha"]):
        raise ValueError(f"ledger item {key}: invalid base SHA")
    if value["author_type"] not in {"BOT", "HUMAN", "UNKNOWN"}:
        raise ValueError(f"ledger item {key}: invalid author type")
    author = _require_mapping(value["author"], f"ledger item {key}.author")
    _require_fields(author, {"login", "identity_source", "app_slug"}, {"login", "identity_source"}, f"ledger item {key}.author")
    if author.get("identity_source") != "github_api":
        raise ValueError(f"ledger item {key}: author identity must come from github_api")
    if value["guardrail_outcome"] not in ALLOWED_OUTCOMES:
        raise ValueError(f"ledger item {key}: invalid guardrail outcome")
    if value["lifecycle_state"] not in STATE_OWNERS or value["current_owner"] != STATE_OWNERS[value["lifecycle_state"]]:
        raise ValueError(f"ledger item {key}: lifecycle state and current owner disagree")
    if value["author_type"] != "BOT" and value["risk_class"] == "ROUTINE":
        raise ValueError(f"ledger item {key}: human or unknown identity cannot be routine")
    for url in _require_list(value["evidence_urls"], f"ledger item {key}.evidence_urls"):
        if not isinstance(url, str) or not URL_RE.fullmatch(url):
            raise ValueError(f"ledger item {key}: evidence URLs must use https")
    attempts = _require_mapping(value["attempts"], f"ledger item {key}.attempts")
    _require_fields(attempts, {"evidence", "recovery", "mutations"}, {"evidence", "recovery", "mutations"}, f"ledger item {key}.attempts")
    if any(not isinstance(attempts[name], int) or attempts[name] < 0 for name in attempts):
        raise ValueError(f"ledger item {key}: attempts must be non-negative integers")
    terminal = value.get("terminal_disposition")
    if value["lifecycle_state"] == "TERMINAL":
        if terminal not in TERMINAL_DISPOSITIONS or value["current_owner"] != "none" or value["next_owner"] != "none":
            raise ValueError(f"ledger item {key}: terminal records require a disposition and no owner")
    elif terminal is not None:
        raise ValueError(f"ledger item {key}: nonterminal records cannot declare a terminal disposition")
    _require_utc(value["updated_at_utc"], f"ledger item {key}.updated_at_utc")


def _validate_calibration(value: Any) -> None:
    calibration = _require_mapping(value, "calibration")
    fields = {"status", "successful_run_count", "required_successful_runs", "scope", "policy_revision", "coverage", "approved_by", "approved_at_utc", "approval_evidence_urls", "invalidated_by_revision", "revoked_at_utc", "rollback_conditions", "completion_authority"}
    _require_fields(calibration, fields, fields, "calibration")
    if calibration["status"] not in {"REPORT_ONLY", "APPROVED", "REVOKED"}:
        raise ValueError("calibration: invalid status")
    if calibration["required_successful_runs"] != 7 or not isinstance(calibration["successful_run_count"], int):
        raise ValueError("calibration: seven successful runs are required")
    if calibration["completion_authority"] != "approve-merge-close-nonsecurity":
        raise ValueError("calibration: unexpected completion authority")
    if calibration["status"] == "APPROVED":
        if not calibration["approved_by"] or not calibration["approved_at_utc"] or not calibration["approval_evidence_urls"]:
            raise ValueError("calibration: approved status requires dated human evidence")
        _require_utc(calibration["approved_at_utc"], "calibration.approved_at_utc")
    if calibration["status"] == "REVOKED" and not calibration["revoked_at_utc"]:
        raise ValueError("calibration: revoked status requires revoked_at_utc")


def _validate_events(events: Any, items: dict[str, dict[str, Any]]) -> None:
    seen_event_ids: set[str] = set()
    seen_idempotency: set[tuple[str, str]] = set()
    for raw in _require_list(events, "events"):
        event = _require_mapping(raw, "event")
        required = {"event_id", "kind", "item_key", "from_owner", "to_owner", "expected_item_revision", "resulting_item_revision", "idempotency_key", "status", "created_at_utc", "acknowledged_at_utc"}
        allowed = required | {"reason"}
        _require_fields(event, allowed, required, "event")
        if event["event_id"] in seen_event_ids:
            raise ValueError(f"event: duplicate event_id {event['event_id']}")
        if event["item_key"] not in items:
            raise ValueError(f"event {event['event_id']}: unknown item key")
        pair = (event["item_key"], event["idempotency_key"])
        if pair in seen_idempotency:
            raise ValueError(f"event {event['event_id']}: duplicate idempotency key for item")
        if event["resulting_item_revision"] != event["expected_item_revision"] + 1:
            raise ValueError(f"event {event['event_id']}: resulting revision must increment by one")
        if event["resulting_item_revision"] > items[event["item_key"]]["revision"]:
            raise ValueError(f"event {event['event_id']}: event revision exceeds item projection")
        if event["idempotency_key"] != f"{event['item_key']}:{event['event_id']}":
            raise ValueError(f"event {event['event_id']}: invalid idempotency key")
        if event["status"] == "ACKNOWLEDGED" and not event["acknowledged_at_utc"]:
            raise ValueError(f"event {event['event_id']}: acknowledgement timestamp required")
        _require_utc(event["created_at_utc"], f"event {event['event_id']}.created_at_utc")
        seen_event_ids.add(event["event_id"])
        seen_idempotency.add(pair)


def _validate_exports() -> None:
    exports = {
        "daily-pr-review.json": True,
        "daily-pr-salvage.json": False,
        "daily-pr-completion.calibration.json": False,
        "daily-pr-completion.json": True,
    }
    directory = ROOT / "docs/cursor-automations/exports"
    for name, expected_approval in exports.items():
        path = directory / name
        try:
            data = json.loads(path.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError) as exc:
            raise ValueError(f"{path}: invalid JSON export: {exc}") from exc
        required = {"name", "triggers", "actions", "prompts", "model", "agentOptions", "memoryEnabled", "scope"}
        if set(data) != required:
            raise ValueError(f"{path}: export must contain exactly the observed Cursor fields")
        if data["memoryEnabled"] is not False:
            raise ValueError(f"{path}: shared memory must be disabled by default")
        approvals = [a for a in data["actions"] if a.get("prComment", {}).get("allowApprove") is True]
        if bool(approvals) != expected_approval:
            raise ValueError(f"{path}: approval action does not match stage authority")
        if any("requestReviewers" in action for action in data["actions"]):
            raise ValueError(f"{path}: reviewer-request action is prohibited")
        source_prompt = (ROOT / "docs/cursor-automations/prompts" / name.replace(".json", ".md").replace("daily-pr-completion.calibration.md", "daily-pr-completion.calibration.md")).read_text(encoding="utf-8").strip() + "\n"
        if data["prompts"][0].get("prompt") != source_prompt:
            raise ValueError(f"{path}: export prompt differs from the checked-in prompt source")


def _validate_prompts() -> None:
    prompts = {
        "daily-pr-review.md": ("GitHub API", "Trunk", "ledger, run records, and lessons"),
        "daily-pr-salvage.md": ("Never approve", "complete Stage 2", "ledger, run records, and lessons"),
        "daily-pr-completion.calibration.md": ("report-only", "successful", "ledger, run records, and lessons"),
        "daily-pr-completion.md": ("TRUNK_QUEUE", "five state-changing actions", "ledger, run records, and lessons"),
    }
    directory = ROOT / "docs/cursor-automations/prompts"
    for name, markers in prompts.items():
        path = directory / name
        try:
            content = path.read_text(encoding="utf-8")
        except OSError as exc:
            raise ValueError(f"{path}: missing required prompt") from exc
        if "Memory is disabled" not in content:
            raise ValueError(f"{path}: prompt must state disabled shared memory")
        if any(marker not in content for marker in markers):
            raise ValueError(f"{path}: missing required lifecycle marker")


def _validate_merge_methods(value: Any, configured_repos: set[str]) -> None:
    seen: set[str] = set()
    for raw in _require_list(value, "repository_merge_methods"):
        entry = _require_mapping(raw, "repository merge method")
        required = {"repository", "method", "required_checks_source", "required_checks", "updated_at_utc"}
        _require_fields(entry, required, required, "repository merge method")
        if entry["repository"] in seen:
            raise ValueError("repository merge method: duplicate repository")
        if entry["method"] not in {"TRUNK_QUEUE", "GITHUB_SQUASH", "GITHUB_MERGE_QUEUE", "UNKNOWN"}:
            raise ValueError("repository merge method: unsupported method")
        if entry["required_checks_source"] not in {"TRUNK", "GITHUB_RULESETS", "GITHUB_BRANCH_PROTECTION", "UNKNOWN"}:
            raise ValueError("repository merge method: unsupported required-check source")
        _require_utc(entry["updated_at_utc"], "repository merge method.updated_at_utc")
        seen.add(entry["repository"])
    if seen != configured_repos:
        raise ValueError("repository merge method: records must match the configured repository set")


def validate(path: Path) -> None:
    ledger = _load_yaml(path)
    root_fields = {"schema_version", "schema_path", "ledger_revision", "calibration", "items", "events", "stage2_work_items", "imports", "repository_merge_methods"}
    _require_fields(ledger, root_fields, root_fields, "ledger")
    if ledger["schema_version"] != "1.1" or ledger["schema_path"] != "schemas/pr-lifecycle-ledger.schema.json":
        raise ValueError("ledger: unsupported schema version or path")
    if not isinstance(ledger["ledger_revision"], int) or ledger["ledger_revision"] < 0:
        raise ValueError("ledger: revision must be a non-negative integer")
    config = _load_yaml(ROOT / "tasks/pr-review-agent.config.yaml")
    configured_repos = set(_require_list(config.get("repos"), "configured repos"))
    _validate_calibration(ledger["calibration"])
    item_keys: set[str] = set()
    items: dict[str, dict[str, Any]] = {}
    for item in _require_list(ledger["items"], "items"):
        _validate_item(item, item_keys)
        items[item["key"]] = item
    _validate_events(ledger["events"], items)
    work_ids: set[str] = set()
    for work_item in _require_list(ledger["stage2_work_items"], "stage2_work_items"):
        work = _require_mapping(work_item, "stage2 work item")
        required = {"work_item_id", "source_item_key", "repository", "pr", "base_sha", "head_sha", "allowed_paths", "prohibited_paths", "repair_description", "required_test_command", "expected_test_result", "acceptance_criteria", "provenance_urls", "expiry_utc", "attempt_count", "current_owner", "creation_event_id", "history"}
        _require_fields(work, required, required, "stage2 work item")
        source = items.get(work["source_item_key"])
        if work["work_item_id"] in work_ids or source is None or work["current_owner"] != "stage2" or source["current_owner"] != "stage2":
            raise ValueError("stage2 work item: duplicate ID, unknown source, or wrong owner")
        if not work["allowed_paths"] or not work["acceptance_criteria"] or not work["provenance_urls"]:
            raise ValueError("stage2 work item: scope, acceptance, and provenance are mandatory")
        _require_utc(work["expiry_utc"], "stage2 work item.expiry_utc")
        work_ids.add(work["work_item_id"])
    seen_imports: set[tuple[str, str]] = set()
    for raw in _require_list(ledger["imports"], "imports"):
        entry = _require_mapping(raw, "import")
        required = {"import_id", "source_path", "source_fingerprint", "status", "created_at_utc"}
        _require_fields(entry, required, required, "import")
        pair = (entry["source_path"], entry["source_fingerprint"])
        if pair in seen_imports:
            raise ValueError("import: duplicate source path/fingerprint")
        _require_utc(entry["created_at_utc"], "import.created_at_utc")
        seen_imports.add(pair)
    _validate_merge_methods(ledger["repository_merge_methods"], configured_repos)
    _validate_prompts()
    _validate_exports()


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("ledger", nargs="?", type=Path, default=ROOT / "tasks/pr-lifecycle-ledger.yaml")
    args = parser.parse_args()
    try:
        validate(args.ledger)
    except ValueError as exc:
        print(f"PR_LIFECYCLE_INVALID: {exc}", file=sys.stderr)
        return 1
    print("PR_LIFECYCLE_VALID")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
