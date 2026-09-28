"""Execute the normative PR lifecycle JSON Schema."""

from __future__ import annotations

import json
from typing import Any

from jsonschema import Draft202012Validator
from pr_lifecycle_support import ROOT


def validate_schema(ledger: dict[str, Any]) -> None:
    schema_path = ROOT / "schemas/pr-lifecycle-ledger.schema.json"
    try:
        schema = json.loads(schema_path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        raise ValueError(f"{schema_path}: invalid JSON Schema: {exc}") from exc
    errors = sorted(Draft202012Validator(schema).iter_errors(ledger), key=str)
    if errors:
        error = errors[0]
        location = ".".join(str(part) for part in error.absolute_path) or "root"
        raise ValueError(f"schema {location}: {error.message}")
