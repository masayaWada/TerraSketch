"""コスト注釈モジュール。

infracost JSON出力を解析し、グラフノードに月額コスト推定を注釈��る。
diffモードではコスト増減の色分けも対応する。
"""

from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path
from typing import Any

import networkx as nx


@dataclass(frozen=True)
class CostInfo:
    """リソースのコスト情報。"""

    monthly_cost: float | None
    hourly_cost: float | None
    currency: str = "USD"

    @property
    def cost_label(self) -> str:
        """表示用コストラベルを生成する。"""
        if self.monthly_cost is None:
            return ""
        return f"${self.monthly_cost:,.2f}/mo"


def parse_infracost(file_path: str | Path) -> dict[str, CostInfo]:
    """infracost JSON出力を解析し、リソースアドレスからコスト情報へのマップを返す。

    Args:
        file_path: infracost JSON出力ファイルのパス
                   （`infracost breakdown --format json` の出力）。

    Returns:
        Terraformリソースアドレス → CostInfo のマッピング。

    Raises:
        FileNotFoundError: ファイルが存在しない場合。
        ValueError: JSON構造が不正な場合。
    """
    path = Path(file_path)
    if not path.exists():
        raise FileNotFoundError(f"Infracost file not found: {path}")

    with open(path, encoding="utf-8") as f:
        data = json.load(f)

    if not isinstance(data, dict):
        raise ValueError("無効なinfracostファイル: JSONルートがオブジェクトではありません。")

    cost_map: dict[str, CostInfo] = {}
    projects = data.get("projects", [])

    for project in projects:
        breakdown = project.get("breakdown", {})
        resources = breakdown.get("resources", [])
        currency = data.get("currency", "USD")

        for resource in resources:
            name = resource.get("name", "")
            monthly = _parse_cost_value(resource.get("monthlyCost"))
            hourly = _parse_cost_value(resource.get("hourlyCost"))

            if name:
                cost_map[name] = CostInfo(
                    monthly_cost=monthly,
                    hourly_cost=hourly,
                    currency=currency,
                )

    return cost_map


def _parse_cost_value(value: Any) -> float | None:
    """コスト値を float に変換する。infracost は文字列で返す場合がある。"""
    if value is None:
        return None
    try:
        return float(value)
    except (ValueError, TypeError):
        return None


def annotate_costs(
    graph: nx.DiGraph,
    cost_map: dict[str, CostInfo],
) -> None:
    """グラフノードにコスト情報を注釈する。

    Args:
        graph: リソース依存関係グラフ（ノードが変更される）。
        cost_map: リソースアドレス → CostInfo のマッピング。
    """
    for node_addr in graph.nodes:
        cost = _find_cost(node_addr, cost_map)
        if cost and cost.monthly_cost is not None:
            graph.nodes[node_addr]["cost_monthly"] = cost.monthly_cost
            graph.nodes[node_addr]["cost_label"] = cost.cost_label


def annotate_cost_diff(
    graph: nx.DiGraph,
    before_costs: dict[str, CostInfo],
    after_costs: dict[str, CostInfo],
) -> None:
    """diffモード時にコスト増減をグラフノードに注釈する。

    Args:
        graph: diff情報付きグラフ。
        before_costs: 変更前のコストマップ。
        after_costs: 変更後のコストマップ。
    """
    for node_addr in graph.nodes:
        before = _find_cost(node_addr, before_costs)
        after = _find_cost(node_addr, after_costs)

        before_val = before.monthly_cost if before and before.monthly_cost is not None else 0.0
        after_val = after.monthly_cost if after and after.monthly_cost is not None else 0.0
        delta = after_val - before_val

        if abs(delta) > 0.01:
            sign = "+" if delta > 0 else ""
            graph.nodes[node_addr]["cost_diff"] = delta
            graph.nodes[node_addr]["cost_diff_label"] = f"[{sign}${delta:,.2f}/mo]"


def _find_cost(
    node_addr: str, cost_map: dict[str, CostInfo]
) -> CostInfo | None:
    """ノードアドレスに対応するコスト情報を検索する。

    infracostのアドレスは module.xxx.type.name 形式の場合があるため、
    完全一致とtype.name の短縮一致の両方で検索する。
    """
    # 完全一致
    if node_addr in cost_map:
        return cost_map[node_addr]

    # infracost側がモジュールパス付きの場合、末尾のtype.nameで一致
    for cost_addr, cost_info in cost_map.items():
        if cost_addr.endswith(f".{node_addr}") or cost_addr == node_addr:
            return cost_info

    return None
