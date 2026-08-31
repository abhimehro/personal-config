"""Safe YAML loading with duplicate-key rejection for lifecycle artifacts."""

from __future__ import annotations

from pathlib import Path
from typing import Any

import yaml
from pr_lifecycle_support import ArtifactValidationError


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
