"""Orchestrate fail-closed PR lifecycle artifact validation."""

from __future__ import annotations

from pathlib import Path

from pr_lifecycle_config import (
    validate_bootstrap_pointer,
    validate_config,
    validate_exports_and_prompts,
)
from pr_lifecycle_ledger import validate_runtime_records
from pr_lifecycle_persist import strip_in_memory_item_fields
from pr_lifecycle_schema import validate_schema
from pr_lifecycle_support import ROOT
from pr_lifecycle_yaml import load_yaml

__all__ = ["validate"]


def validate(runtime_ledger: Path) -> int:
    """Validate policy plus one fetched runtime ledger; strip known projection keys."""
    config = load_yaml(ROOT / "tasks/pr-review-agent.config.yaml")
    validate_config(config)
    pointer = load_yaml(ROOT / "tasks/pr-lifecycle-ledger.yaml")
    validate_bootstrap_pointer(pointer, config)
    ledger = load_yaml(runtime_ledger)
    stripped = strip_in_memory_item_fields(ledger)
    validate_schema(ledger)
    validate_runtime_records(ledger, config)
    validate_exports_and_prompts(config)
    return stripped
