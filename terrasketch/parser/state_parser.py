"""Terraform state JSON パーサー。

`terraform show -json` で出力されたstate JSONを解析し、
構造化されたResourceオブジェクトとしてリソースを抽出する。
"""

from __future__ import annotations

import json
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any


@dataclass
class Resource:
    """Terraform stateから抽出された単一リソースを表すデータクラス。"""

    id: str
    type: str
    name: str
    provider: str
    attributes: dict[str, Any] = field(default_factory=dict)

    @property
    def address(self) -> str:
        return f"{self.type}.{self.name}"


def _extract_resources_from_module(module: dict[str, Any]) -> list[Resource]:
    """モジュールおよび子モジュールからリソースを再帰的に抽出する。"""
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
    """Terraform state JSONファイルを解析し、Resourceリストを返す。

    Args:
        file_path: Terraform state JSONファイルのパス
                   （`terraform show -json` の出力）。

    Returns:
        stateから抽出されたResourceオブジェクトのリスト。

    Raises:
        FileNotFoundError: stateファイルが存在しない場合。
        ValueError: JSON構造が不正、または期待するキーが欠落している場合。
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
