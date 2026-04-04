"""Terraform / OpenTofu state JSON パーサー。

`terraform show -json` または `tofu show -json` で出力されたstate JSONを解析し、
構造化されたResourceオブジェクトとしてリソースを抽出する。
"""

from __future__ import annotations

import json
import logging
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

logger = logging.getLogger("terrasketch")


@dataclass
class Resource:
    """Terraform stateから抽出された単一リソースを表すデータクラス。"""

    id: str
    type: str
    name: str
    provider: str
    attributes: dict[str, Any] = field(default_factory=dict)
    module_path: str = ""

    @property
    def address(self) -> str:
        return f"{self.type}.{self.name}"


def _extract_resources_from_module(
    module: dict[str, Any],
    module_path: str = "",
) -> list[Resource]:
    """モジュールおよび子モジュールからリソースを再帰的に抽出する。

    Args:
        module: Terraform stateのモジュール辞書。
        module_path: 現在のモジュールパス（例: 'module.vpc.module.subnets'）。
    """
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
            module_path=module_path,
        )
        resources.append(resource)

    for child in module.get("child_modules", []):
        # child_modulesにはaddressフィールドがある（例: 'module.vpc'）
        child_source = child.get("address", "")
        child_path = f"{module_path}.{child_source}" if module_path else child_source
        resources.extend(_extract_resources_from_module(child, child_path))

    return resources


def detect_runtime(state: dict[str, Any]) -> str:
    """state JSONからランタイム（terraform/opentofu）を自動検出する。

    Args:
        state: パース済みのstate JSON辞書。

    Returns:
        'opentofu' または 'terraform'。
    """
    if "opentofu_version" in state:
        return "opentofu"
    return "terraform"


def parse_state(file_path: str | Path, runtime: str = "auto") -> list[Resource]:
    """Terraform / OpenTofu state JSONファイルを解析し、Resourceリストを返す。

    Args:
        file_path: state JSONファイルのパス
                   （`terraform show -json` または `tofu show -json` の出力）。
        runtime: ランタイム指定（'terraform', 'opentofu', 'auto'）。
                 'auto' の場合はJSONの内容から自動検出する。

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

    # ランタイム検出
    detected = detect_runtime(state)
    if runtime == "auto":
        runtime = detected
    if runtime == "opentofu":
        version = state.get("opentofu_version", "不明")
        logger.info("OpenTofu state を検出しました（バージョン: %s）", version)
    else:
        version = state.get("terraform_version", "不明")
        logger.info("Terraform state を検出しました（バージョン: %s）", version)

    values = state.get("values")
    if values is None:
        raise ValueError("Invalid state file: missing 'values' key.")

    root_module = values.get("root_module")
    if root_module is None:
        raise ValueError("Invalid state file: missing 'values.root_module' key.")

    return _extract_resources_from_module(root_module)
