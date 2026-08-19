"""Cross-record lifecycle-ledger validation that JSON Schema cannot express."""

from __future__ import annotations

from typing import Any

from pr_lifecycle_support import (
    KEY_RE,
    SHA_RE,
    require_https_url,
    require_https_urls,
    require_list,
    require_mapping,
    require_utc,
)

ALLOWED_OUTCOMES = {
    "PASS_ROUTINE", "REVIEW_SECURITY", "HOLD_CONTRACT", "HOLD_EVIDENCE",
    "HOLD_PLATFORM", "HOLD_CANONICAL", "CLOSE_NONSECURITY_NOOP",
    "ANALYSIS_ERROR", "NOT_RUN",
}
TERMINAL_DISPOSITIONS = {
    "MERGED_ROUTINE", "MERGED_BOUNDED_COMPLETION", "CLOSED_NOOP",
    "CLOSED_DUPLICATE", "CLOSED_STALE", "CLOSED_SUPERSEDED",
    "HUMAN_REJECTED", "HUMAN_DEFERRED",
}
STATE_OWNERS = {
    "STAGE1_INTAKE": "stage1", "STAGE2_QUEUED": "stage2",
    "STAGE2_ACTIVE": "stage2", "STAGE3_RECONCILIATION": "stage3",
    "WAITING_HUMAN": "human", "TERMINAL": "none",
}


def validate_runtime_records(ledger: dict[str, Any], config: dict[str, Any]) -> None:
    items = validate_items(ledger["items"])
    calibration_events = validate_events(ledger["events"], items)
    validate_calibration(ledger["calibration"], calibration_events, config)
    validate_work_items(ledger["stage2_work_items"], items)
    validate_imports(ledger["imports"])
    validate_merge_methods(ledger["repository_merge_methods"], set(config["repos"]))


def validate_items(value: Any) -> dict[str, dict[str, Any]]:
    seen: set[str] = set()
    items = {}
    for raw in require_list(value, "items"):
        item = validate_item(raw, seen)
        items[item["key"]] = item
    return items


def validate_item(item: Any, seen_keys: set[str]) -> dict[str, Any]:
    value = require_mapping(item, "ledger item")
    key = value["key"]
    if key in seen_keys:
        raise ValueError(f"ledger item: duplicate key {key}")
    seen_keys.add(key)
    validate_item_identity(value, key)
    validate_item_state(value, key)
    require_https_urls(value["evidence_urls"], f"ledger item {key}.evidence_urls")
    require_utc(value["updated_at_utc"], f"ledger item {key}.updated_at_utc")
    return value


def validate_item_identity(value: dict[str, Any], key: str) -> None:
    validate_item_key(value, key)
    validate_item_anchors(value, key)
    validate_item_author(value, key)


def validate_item_key(value: dict[str, Any], key: str) -> None:
    if not KEY_RE.fullmatch(key):
        raise ValueError("ledger item: invalid key")
    if not key.startswith(f"{value['repository']}#{value['pr']}@"):
        raise ValueError(f"ledger item {key}: key does not match repository and PR")


def validate_item_anchors(value: dict[str, Any], key: str) -> None:
    if not SHA_RE.fullmatch(value["head_sha"]) or not key.endswith(value["head_sha"]):
        raise ValueError(f"ledger item {key}: key/head SHA mismatch")
    if not SHA_RE.fullmatch(value["base_sha"]):
        raise ValueError(f"ledger item {key}: invalid base SHA")


def validate_item_author(value: dict[str, Any], key: str) -> None:
    author = require_mapping(value["author"], f"ledger item {key}.author")
    if author["identity_source"] != "github_api":
        raise ValueError(f"ledger item {key}: identity source must be github_api")
    if value["author_type"] != "BOT" and value["risk_class"] == "ROUTINE":
        raise ValueError(f"ledger item {key}: non-bot identity cannot be routine")


def validate_item_state(value: dict[str, Any], key: str) -> None:
    validate_item_guardrail_outcome(value, key)
    validate_item_owner(value, key)
    validator = {"TERMINAL": validate_terminal_item_state}.get(
        value["lifecycle_state"], validate_nonterminal_item_state
    )
    validator(value, key)


def validate_item_guardrail_outcome(value: dict[str, Any], key: str) -> None:
    if value["guardrail_outcome"] not in ALLOWED_OUTCOMES:
        raise ValueError(f"ledger item {key}: invalid guardrail outcome")


def validate_item_owner(value: dict[str, Any], key: str) -> None:
    if STATE_OWNERS[value["lifecycle_state"]] != value["current_owner"]:
        raise ValueError(f"ledger item {key}: lifecycle state and owner disagree")


def validate_terminal_item_state(value: dict[str, Any], key: str) -> None:
    terminal = value.get("terminal_disposition")
    if not all((terminal in TERMINAL_DISPOSITIONS, value["next_owner"] == "none")):
        raise ValueError(f"ledger item {key}: terminal record requires disposition/no owner")


def validate_nonterminal_item_state(value: dict[str, Any], key: str) -> None:
    terminal = value.get("terminal_disposition")
    if terminal is not None:
        raise ValueError(f"ledger item {key}: nonterminal record cannot carry a disposition")
    if value["next_owner"] == "none":
        raise ValueError(f"ledger item {key}: nonterminal record requires next owner")


def validate_events(events: Any, items: dict[str, dict[str, Any]]) -> list[dict[str, Any]]:
    seen_ids: set[str] = set()
    seen_keys: set[tuple[str, str]] = set()
    projected: dict[str, int] = {}
    calibration_events: list[dict[str, Any]] = []
    for raw in require_list(events, "events"):
        event = require_mapping(raw, "event")
        event_id = event["event_id"]
        if event_id in seen_ids:
            raise ValueError(f"event: duplicate event ID {event_id}")
        seen_ids.add(event_id)
        require_utc(event["created_at_utc"], f"event {event_id}.created_at_utc")
        if event["acknowledged_at_utc"] is not None:
            require_utc(event["acknowledged_at_utc"], f"event {event_id}.acknowledged_at_utc")
        if event["kind"] == "CALIBRATION":
            validate_calibration_event(event, seen_keys)
            calibration_events.append(event)
        else:
            validate_item_event(event, items, seen_keys, projected)
    validate_projection(items, projected)
    return calibration_events


def validate_calibration_event(event: dict[str, Any], seen_keys: set[tuple[str, str]]) -> None:
    event_id = event["event_id"]
    pair = ("__calibration__", event["idempotency_key"])
    valid = event["item_key"] is None and pair not in seen_keys
    valid = valid and event["policy_revision"] and event["successful"] is True
    valid = valid and event["expected_item_revision"] == 0
    valid = valid and event["resulting_item_revision"] == 0
    if not valid:
        raise ValueError(f"event {event_id}: invalid calibration event")
    seen_keys.add(pair)


def validate_item_event(
    event: dict[str, Any],
    items: dict[str, dict[str, Any]],
    seen_keys: set[tuple[str, str]],
    projected: dict[str, int],
) -> None:
    item_key, pair = validate_item_event_reference(event, items, seen_keys)
    validate_item_event_revision(event, item_key, projected)
    validate_item_event_acknowledgement(event, item_key)
    seen_keys.add(pair)
    projected[item_key] = event["resulting_item_revision"]


def validate_item_event_reference(
    event: dict[str, Any],
    items: dict[str, dict[str, Any]],
    seen_keys: set[tuple[str, str]],
) -> tuple[str, tuple[str, str]]:
    event_id = event["event_id"]
    item_key = event["item_key"]
    pair = (item_key, event["idempotency_key"])
    if item_key not in items or pair in seen_keys:
        raise ValueError(f"event {event_id}: unknown item or duplicate idempotency key")
    if event["idempotency_key"] != f"{item_key}:{event_id}":
        raise ValueError(f"event {event_id}: invalid idempotency key")
    return item_key, pair


def validate_item_event_revision(
    event: dict[str, Any], item_key: str, projected: dict[str, int]
) -> None:
    event_id = event["event_id"]
    if event["resulting_item_revision"] != event["expected_item_revision"] + 1:
        raise ValueError(f"event {event_id}: revision must increment by one")
    if event["expected_item_revision"] != projected.get(item_key, 0):
        raise ValueError(f"event {event_id}: stale or discontinuous item projection")


def validate_item_event_acknowledgement(event: dict[str, Any], item_key: str) -> None:
    event_id = event["event_id"]
    if event["status"] == "ACKNOWLEDGED" and not event["acknowledged_at_utc"]:
        raise ValueError(f"event {event_id}: acknowledgement timestamp required")


def validate_projection(items: dict[str, dict[str, Any]], projected: dict[str, int]) -> None:
    for item_key, item in items.items():
        revision = projected.get(item_key, 0)
        if revision != item["revision"]:
            raise ValueError(f"ledger item {item_key}: projection revision lacks latest event")


def validate_calibration(
    calibration: dict[str, Any],
    events: list[dict[str, Any]],
    config: dict[str, Any],
) -> None:
    lifecycle = require_mapping(config["lifecycle"], "config.lifecycle")
    count = calibration["successful_run_count"]
    required = calibration["required_successful_runs"]
    validate_calibration_count(calibration, count, required)
    policy_matches = validate_calibration_policy(calibration, lifecycle["policy_revision"], count)
    validate_calibration_event_count(calibration, events, count)
    validate_approval(calibration, count, required, policy_matches)


def validate_calibration_count(
    calibration: dict[str, Any],
    count: int,
    required: int,
) -> None:
    if not is_valid_successful_count(count, required):
        raise ValueError("calibration: successful count must be between zero and seven")
    if calibration["completion_authority"] != "approve-merge-close-nonsecurity":
        raise ValueError("calibration: unexpected completion authority")


def is_valid_successful_count(count: int, required: int) -> bool:
    if required != 7:
        return False
    if not isinstance(count, int):
        return False
    return 0 <= count <= required


def validate_calibration_policy(
    calibration: dict[str, Any],
    current_policy: str,
    count: int,
) -> bool:
    policy_matches = calibration["policy_revision"] == current_policy
    if policy_matches:
        return True
    validate_stale_calibration_reset(calibration, current_policy, count)
    return False


def validate_stale_calibration_reset(
    calibration: dict[str, Any], current_policy: str, count: int
) -> None:
    if calibration["invalidated_by_revision"] != current_policy:
        raise ValueError("calibration: stale policy must be invalidated and reset")
    if calibration["status"] != "REPORT_ONLY":
        raise ValueError("calibration: stale policy must be invalidated and reset")
    if count != 0:
        raise ValueError("calibration: stale policy must be invalidated and reset")


def validate_calibration_event_count(
    calibration: dict[str, Any],
    events: list[dict[str, Any]],
    count: int,
) -> None:
    matching = [event for event in events if event["policy_revision"] == calibration["policy_revision"]]
    if len(matching) != count:
        raise ValueError("calibration: successful count must match current-policy events")


def validate_approval(
    calibration: dict[str, Any],
    count: int,
    required: int,
    policy_matches: bool,
) -> None:
    if calibration["status"] == "APPROVED":
        validate_approved_calibration(calibration, count, required, policy_matches)
    elif calibration["status"] == "REVOKED":
        validate_revoked_calibration(calibration)


def validate_approved_calibration(
    calibration: dict[str, Any], count: int, required: int, policy_matches: bool
) -> None:
    prerequisites = (
        count >= required,
        policy_matches,
        not calibration["invalidated_by_revision"],
        calibration["approved_by"],
        calibration["approved_at_utc"],
        calibration["approval_evidence_urls"],
    )
    if not all(prerequisites):
        raise ValueError("calibration: approval requires seven current successful runs")
    require_utc(calibration["approved_at_utc"], "calibration.approved_at_utc")
    require_https_urls(calibration["approval_evidence_urls"], "calibration.approval_evidence_urls")


def validate_revoked_calibration(calibration: dict[str, Any]) -> None:
    if not calibration["revoked_at_utc"]:
        raise ValueError("calibration: revoked status requires timestamp")


def validate_work_items(value: Any, items: dict[str, dict[str, Any]]) -> None:
    seen: set[str] = set()
    for raw in require_list(value, "stage2_work_items"):
        work = require_mapping(raw, "stage2 work item")
        validate_work_item_identity(work, items, seen)
        validate_work_item_scope(work)
        validate_work_item_evidence(work)
        seen.add(work["work_item_id"])


def validate_work_item_identity(
    work: dict[str, Any], items: dict[str, dict[str, Any]], seen: set[str]
) -> None:
    work_item_id = work["work_item_id"]
    if work_item_id in seen:
        raise ValueError("stage2 work item: duplicate ID, source, or owner failure")
    source = items.get(work["source_item_key"])
    if source is None:
        raise ValueError("stage2 work item: duplicate ID, source, or owner failure")
    validate_work_item_owners(work, source)


def validate_work_item_owners(work: dict[str, Any], source: dict[str, Any]) -> None:
    if work["current_owner"] != "stage2":
        raise ValueError("stage2 work item: duplicate ID, source, or owner failure")
    if source["current_owner"] != "stage2":
        raise ValueError("stage2 work item: duplicate ID, source, or owner failure")


def validate_work_item_scope(work: dict[str, Any]) -> None:
    if not work["allowed_paths"]:
        raise ValueError("stage2 work item: scope and acceptance are mandatory")
    if not work["acceptance_criteria"]:
        raise ValueError("stage2 work item: scope and acceptance are mandatory")


def validate_work_item_evidence(work: dict[str, Any]) -> None:
    require_https_urls(work["provenance_urls"], "stage2 work item.provenance_urls")
    require_utc(work["expiry_utc"], "stage2 work item.expiry_utc")


def validate_imports(value: Any) -> None:
    seen: set[tuple[str, str]] = set()
    for raw in require_list(value, "imports"):
        entry = require_mapping(raw, "import")
        pair = (entry["source_path"], entry["source_fingerprint"])
        if pair in seen:
            raise ValueError("import: duplicate source path/fingerprint")
        require_utc(entry["created_at_utc"], "import.created_at_utc")
        seen.add(pair)


def validate_merge_methods(value: Any, configured_repos: set[str]) -> None:
    seen: set[str] = set()
    for raw in require_list(value, "repository_merge_methods"):
        entry = require_mapping(raw, "repository merge method")
        validate_merge_method_entry(entry, seen)
    if seen != configured_repos:
        raise ValueError("repository merge method: records must match configured repos")


def validate_merge_method_entry(entry: dict[str, Any], seen: set[str]) -> None:
    repository = entry["repository"]
    if repository in seen:
        raise ValueError("repository merge method: duplicate repository")
    seen.add(repository)
    require_utc(entry["updated_at_utc"], "repository merge method.updated_at_utc")
    validator = {"VERIFIED": validate_verified_merge_method}.get(
        entry["discovery_status"], validate_pending_merge_method
    )
    validator(entry)


def validate_pending_merge_method(entry: dict[str, Any]) -> None:
    if not entry["hold_reason"]:
        raise ValueError("repository merge method: pending record requires explicit hold")
    if entry["required_checks_verified_zero"]:
        raise ValueError("repository merge method: pending record requires explicit hold")


def validate_verified_merge_method(entry: dict[str, Any]) -> None:
    validate_known_merge_method(entry)
    validate_verified_merge_evidence(entry)
    validate_verified_merge_hold(entry)


def validate_known_merge_method(entry: dict[str, Any]) -> None:
    if "UNKNOWN" in {entry["method"], entry["required_checks_source"]}:
        raise ValueError("repository merge method: verified record cannot be unknown")


def validate_verified_merge_evidence(entry: dict[str, Any]) -> None:
    require_https_url(entry["evidence_url"], "repository merge method.evidence_url")
    require_utc(entry["observed_at_utc"], "repository merge method.observed_at_utc")


def validate_verified_merge_hold(entry: dict[str, Any]) -> None:
    if entry["hold_reason"] is not None:
        raise ValueError("repository merge method: verified record cannot have hold")
    empty = not entry["required_checks"]
    if empty != entry["required_checks_verified_zero"]:
        raise ValueError("repository merge method: empty checks require verified-zero proof")
