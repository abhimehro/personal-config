"""Shared parsing, format, and JSON Schema helpers for PR lifecycle validation."""

from __future__ import annotations

import json
import re
from pathlib import Path
from typing import Any
from urllib.parse import urlparse

import yaml
from jsonschema import Draft202012Validator


class ArtifactValidationError(ValueError):
    """A fail-closed lifecycle source or runtime-artifact validation error."""


ROOT = Path(__file__).resolve().parents[1]
KEY_RE = re.compile(r"^[A-Za-z0-9_.-]+/[A-Za-z0-9_.-]+#[1-9][0-9]*@[0-9a-f]{40}$")
SHA_RE = re.compile(r"^[0-9a-f]{40}$")
UTC_RE = re.compile(r"^\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}(?:\.\d+)?Z$")
URL_RE = re.compile(r"^https://[^\s]+$")


class UniqueKeyLoader(yaml.SafeLoader):
    """YAML loader that rejects duplicate mapping keys."""


def _construct_mapping(
    loader: UniqueKeyLoader,
    node: yaml.MappingNode,
    deep: bool = False,
) -> dict[Any, Any]:
    mapping: dict[Any, Any] = {}
    for key_node, value_node in node.value:
        key = loader.construct_object(key_node, deep=deep)
        if key in mapping:
            raise ValueError(f"duplicate YAML key: {key!r}")
        mapping[key] = loader.construct_object(value_node, deep=deep)
    return mapping


UniqueKeyLoader.add_constructor(
    yaml.resolver.BaseResolver.DEFAULT_MAPPING_TAG,
    _construct_mapping,
)


def load_yaml(path: Path) -> dict[str, Any]:
    try:
        loader = UniqueKeyLoader(path.read_text(encoding="utf-8"))
        try:
            data = loader.get_single_data()
        finally:
            loader.dispose()
    except (OSError, yaml.YAMLError, ValueError) as exc:
        raise ValueError(f"{path}: invalid YAML: {exc}") from exc
    if not isinstance(data, dict):
        raise ArtifactValidationError(f"{path}: root must be a mapping")
    return data


def require_mapping(value: Any, label: str) -> dict[str, Any]:
    if not isinstance(value, dict):
        raise ArtifactValidationError(f"{label}: expected mapping")
    return value


def require_list(value: Any, label: str) -> list[Any]:
    if not isinstance(value, list):
        raise ArtifactValidationError(f"{label}: expected list")
    return value


def require_fields(
    value: dict[str, Any],
    allowed: set[str],
    required: set[str],
    label: str,
) -> None:
    unknown = set(value) - allowed
    missing = required - set(value)
    if unknown:
        raise ValueError(f"{label}: unsupported fields: {sorted(unknown)}")
    if missing:
        raise ValueError(f"{label}: missing required fields: {sorted(missing)}")


def require_utc(value: Any, label: str) -> None:
    if not isinstance(value, str) or not UTC_RE.fullmatch(value):
        raise ValueError(f"{label}: expected RFC 3339 UTC timestamp")


def require_https_url(value: Any, label: str) -> None:
    if not isinstance(value, str) or not URL_RE.fullmatch(value):
        raise ValueError(f"{label}: expected complete https URL")
    parsed = urlparse(value)
    if parsed.scheme != "https" or not parsed.netloc:
        raise ValueError(f"{label}: expected complete https URL")


def require_https_urls(value: Any, label: str) -> None:
    for index, url in enumerate(require_list(value, label)):
        require_https_url(url, f"{label}[{index}]")


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
