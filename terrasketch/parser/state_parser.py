"""Terraform state JSON parser.

Parses terraform state JSON (from `terraform show -json`) and extracts
resources into structured Resource objects.
"""

from __future__ import annotations

import json
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any


@dataclass
class Resource:
    """Represents a single Terraform resource extracted from state."""

    id: str
    type: str
    name: str
    provider: str
    attributes: dict[str, Any] = field(default_factory=dict)

    @property
    def address(self) -> str:
        return f"{self.type}.{self.name}"


def _extract_resources_from_module(module: dict[str, Any]) -> list[Resource]:
    """Recursively extract resources from a module and its child modules."""
    resources: list[Resource] = []

    for res in module.get("resources", []):
        attrs = res.get("values", {})
        provider = res.get("provider_name", "")
        resource = Resource(
            id=attrs.get("id", res.get("address", "")),
            type=res.get("type", ""),
            name=res.get("name", ""),
            provider=provider,
            attributes=attrs,
        )
        resources.append(resource)

    for child in module.get("child_modules", []):
        resources.extend(_extract_resources_from_module(child))

    return resources


def parse_state(file_path: str | Path) -> list[Resource]:
    """Parse a Terraform state JSON file and return a list of Resources.

    Args:
        file_path: Path to the terraform state JSON file
                   (output of `terraform show -json`).

    Returns:
        List of Resource objects extracted from the state.

    Raises:
        FileNotFoundError: If the state file does not exist.
        ValueError: If the JSON structure is invalid or missing expected keys.
    """
    path = Path(file_path)
    if not path.exists():
        raise FileNotFoundError(f"State file not found: {path}")

    with open(path, encoding="utf-8") as f:
        state = json.load(f)

    values = state.get("values")
    if values is None:
        raise ValueError("Invalid state file: missing 'values' key.")

    root_module = values.get("root_module")
    if root_module is None:
        raise ValueError("Invalid state file: missing 'values.root_module' key.")

    return _extract_resources_from_module(root_module)
