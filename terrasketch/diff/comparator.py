"""Terraform state diff比較モジュール。

2つのTerraform state JSONを比較し、リソースの追加・削除・変更を検出する。
検出結果をグラフのノード属性として付与し、レンダラーで色分け可視化する。
"""

from __future__ import annotations

from enum import Enum
from typing import Any

import networkx as nx

from terrasketch.graph.builder import build_graph
from terrasketch.parser.state_parser import Resource, parse_state


class DiffStatus(str, Enum):
    """リソースのdiffステータス。"""

    ADDED = "added"
    REMOVED = "removed"
    MODIFIED = "modified"
    UNCHANGED = "unchanged"


def compare_states(
    before_path: str,
    after_path: str,
) -> tuple[list[Resource], dict[str, DiffStatus], dict[str, dict[str, Any]]]:
    """2つのstateファイルを比較し、差分情報を返す。

    Args:
        before_path: 変更前のstate JSONファイルパス。
        after_path: 変更後のstate JSONファイルパス。

    Returns:
        (全リソースリスト, アドレス→diffステータスのマッピング,
         アドレス→変更属性のマッピング) のタプル。
    """
    before_resources = parse_state(before_path)
    after_resources = parse_state(after_path)

    before_map: dict[str, Resource] = {r.address: r for r in before_resources}
    after_map: dict[str, Resource] = {r.address: r for r in after_resources}

    all_addresses = set(before_map.keys()) | set(after_map.keys())
    diff_status: dict[str, DiffStatus] = {}
    changed_attrs: dict[str, dict[str, Any]] = {}

    for addr in all_addresses:
        if addr not in before_map:
            diff_status[addr] = DiffStatus.ADDED
        elif addr not in after_map:
            diff_status[addr] = DiffStatus.REMOVED
        else:
            # 属性を比較
            before_attrs = before_map[addr].attributes
            after_attrs = after_map[addr].attributes
            changes = _diff_attributes(before_attrs, after_attrs)
            if changes:
                diff_status[addr] = DiffStatus.MODIFIED
                changed_attrs[addr] = changes
            else:
                diff_status[addr] = DiffStatus.UNCHANGED

    # 全リソースを統合（削除されたものも含む）
    all_resources: list[Resource] = []
    seen: set[str] = set()
    for r in after_resources:
        all_resources.append(r)
        seen.add(r.address)
    for r in before_resources:
        if r.address not in seen:
            all_resources.append(r)

    return all_resources, diff_status, changed_attrs


def _diff_attributes(
    before: dict[str, Any], after: dict[str, Any]
) -> dict[str, Any]:
    """2つの属性辞書の差分を検出する。

    Returns:
        変更があったキーとその新旧値の辞書。空なら変更なし。
    """
    changes: dict[str, Any] = {}
    all_keys = set(before.keys()) | set(after.keys())

    for key in all_keys:
        # id, tagsなど頻繁に変わる属性を除外するのではなく全属性を比較
        old_val = before.get(key)
        new_val = after.get(key)
        if old_val != new_val:
            changes[key] = {"before": old_val, "after": new_val}

    return changes


def build_diff_graph(
    resources: list[Resource],
    diff_status: dict[str, DiffStatus],
    changed_attrs: dict[str, dict[str, Any]],
) -> nx.DiGraph:
    """diff情報付きのリソースグラフを構築する。

    Args:
        resources: 全リソースリスト（before + after統合）。
        diff_status: アドレス→diffステータスのマッピング。
        changed_attrs: アドレス→変更属性のマッピング。

    Returns:
        ノードにdiff_status属性が付与されたDiGraph。
    """
    graph = build_graph(resources)

    for node_addr in graph.nodes:
        status = diff_status.get(node_addr, DiffStatus.UNCHANGED)
        graph.nodes[node_addr]["diff_status"] = status.value
        if node_addr in changed_attrs:
            graph.nodes[node_addr]["changed_attrs"] = changed_attrs[node_addr]

    return graph


# diff表示用のスタイル定義
DIFF_COLORS = {
    DiffStatus.ADDED: {"fill": "#c8e6c9", "stroke": "#2e7d32", "label": "[NEW]"},
    DiffStatus.REMOVED: {"fill": "#ffcdd2", "stroke": "#c62828", "label": "[DEL]"},
    DiffStatus.MODIFIED: {"fill": "#fff9c4", "stroke": "#f57f17", "label": "[MOD]"},
    DiffStatus.UNCHANGED: {"fill": None, "stroke": None, "label": ""},
}
