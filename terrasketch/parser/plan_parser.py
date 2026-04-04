"""Terraform plan JSON パーサー。

`terraform show -json <planfile>` で出力されたplan JSONを解析し、
リソースリストとdiffステータスを抽出する。
既存のdiff機構と同じ形式で出力し、レンダラーの色分け表示を再利用する。
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from terrasketch.diff.comparator import DiffStatus
from terrasketch.parser.state_parser import Resource


# plan JSONのaction → DiffStatus の変換マップ
_ACTION_MAP: dict[str, DiffStatus] = {
    "create": DiffStatus.ADDED,
    "delete": DiffStatus.REMOVED,
    "update": DiffStatus.MODIFIED,
    "read": DiffStatus.UNCHANGED,
    "no-op": DiffStatus.UNCHANGED,
}


def parse_plan(
    file_path: str | Path,
) -> tuple[list[Resource], dict[str, DiffStatus], dict[str, dict[str, Any]]]:
    """Terraform plan JSONファイルを解析し、リソースリストとdiffステータスを返す。

    Args:
        file_path: `terraform show -json <planfile>` の出力ファイルパス。

    Returns:
        (リソースリスト, アドレス→DiffStatus, アドレス→変更属性) のタプル。
        既存のdiff_generate()と同じ形式で返すため、レンダラーを共有可能。

    Raises:
        FileNotFoundError: planファイルが存在しない場合。
        ValueError: JSON構造が不正、または必要なキーが欠落している場合。
    """
    path = Path(file_path)
    if not path.exists():
        raise FileNotFoundError(f"Plan file not found: {path}")

    with open(path, encoding="utf-8") as f:
        plan = json.load(f)

    # plan JSON構造の検証
    if "planned_values" not in plan:
        raise ValueError(
            "無効なplanファイル: 'planned_values' キーが見つかりません。\n"
            "ヒント: `terraform show -json <planfile>` の出力を使用してください。"
        )

    # resource_changes から各リソースのアクションと変更属性を抽出
    resource_changes = plan.get("resource_changes", [])
    action_map: dict[str, DiffStatus] = {}
    changed_attrs: dict[str, dict[str, Any]] = {}

    for change_entry in resource_changes:
        addr = change_entry.get("address", "")
        actions = change_entry.get("change", {}).get("actions", [])

        # actionsは配列: ["create"], ["delete"], ["update"], ["no-op"],
        # ["create", "delete"]（置換）等
        status = _resolve_action(actions)
        action_map[addr] = status

        # 変更属性の抽出（update時）
        if status == DiffStatus.MODIFIED:
            before = change_entry.get("change", {}).get("before", {}) or {}
            after = change_entry.get("change", {}).get("after", {}) or {}
            changes = _extract_changes(before, after)
            if changes:
                changed_attrs[addr] = changes

    # planned_values からリソースを抽出
    planned_values = plan["planned_values"]
    root_module = planned_values.get("root_module", {})
    resources = _extract_planned_resources(root_module)

    # resource_changes に含まれるが planned_values にないリソース（削除予定）を追加
    resource_addrs = {r.address for r in resources}
    for change_entry in resource_changes:
        addr = change_entry.get("address", "")
        if addr not in resource_addrs:
            actions = change_entry.get("change", {}).get("actions", [])
            if "delete" in actions:
                before_vals = change_entry.get("change", {}).get("before", {}) or {}
                rtype = change_entry.get("type", "")
                rname = change_entry.get("name", "")
                resources.append(Resource(
                    id=before_vals.get("id", addr),
                    type=rtype,
                    name=rname,
                    provider=change_entry.get("provider_name", ""),
                    attributes=before_vals,
                    module_path=change_entry.get("module_address", ""),
                ))
                resource_addrs.add(addr)

    # アクション未設定のリソースはUNCHANGEDとする
    for r in resources:
        if r.address not in action_map:
            action_map[r.address] = DiffStatus.UNCHANGED

    return resources, action_map, changed_attrs


def _resolve_action(actions: list[str]) -> DiffStatus:
    """plan JSONのactionsリストからDiffStatusを解決する。

    Args:
        actions: ["create"], ["delete"], ["update"], ["no-op"],
                 ["delete", "create"]（置換）等。
    """
    if not actions:
        return DiffStatus.UNCHANGED

    # 置換（delete+create）はMODIFIED扱い
    action_set = set(actions)
    if "create" in action_set and "delete" in action_set:
        return DiffStatus.MODIFIED
    if "create" in action_set:
        return DiffStatus.ADDED
    if "delete" in action_set:
        return DiffStatus.REMOVED
    if "update" in action_set:
        return DiffStatus.MODIFIED

    return DiffStatus.UNCHANGED


def _extract_changes(
    before: dict[str, Any], after: dict[str, Any]
) -> dict[str, Any]:
    """before/afterの属性差分を抽出する。"""
    changes: dict[str, Any] = {}
    all_keys = set(before.keys()) | set(after.keys())
    for key in all_keys:
        old_val = before.get(key)
        new_val = after.get(key)
        if old_val != new_val:
            changes[key] = {"before": old_val, "after": new_val}
    return changes


def _extract_planned_resources(
    module: dict[str, Any],
    module_path: str = "",
) -> list[Resource]:
    """planned_valuesのモジュール構造からリソースを再帰的に抽出する。"""
    resources: list[Resource] = []

    for res in module.get("resources", []):
        attrs = res.get("values", {})
        resources.append(Resource(
            id=attrs.get("id", res.get("address", "")),
            type=res.get("type", ""),
            name=res.get("name", ""),
            provider=res.get("provider_name", ""),
            attributes=attrs,
            module_path=module_path,
        ))

    for child in module.get("child_modules", []):
        child_addr = child.get("address", "")
        child_path = f"{module_path}.{child_addr}" if module_path else child_addr
        resources.extend(_extract_planned_resources(child, child_path))

    return resources
