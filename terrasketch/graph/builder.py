"""Terraformリソースのグラフビルダー。

リソース間の属性参照に基づいて、依存関係を表す
有向グラフ（DiGraph）を構築する。
"""

from __future__ import annotations

import networkx as nx

from terrasketch.parser.state_parser import Resource


# (リソースタイプ, 属性名) -> 参照先リソースタイプ のマッピング。
# 属性値は参照先リソースのIDであることを想定。
_AWS_RELATIONSHIP_RULES: list[tuple[str, str, str]] = [
    ("aws_subnet", "vpc_id", "aws_vpc"),
    ("aws_instance", "subnet_id", "aws_subnet"),
    ("aws_security_group", "vpc_id", "aws_vpc"),
    ("aws_instance", "vpc_security_group_ids", "aws_security_group"),
    ("aws_network_interface", "subnet_id", "aws_subnet"),
    ("aws_nat_gateway", "subnet_id", "aws_subnet"),
    ("aws_route_table", "vpc_id", "aws_vpc"),
    ("aws_internet_gateway", "vpc_id", "aws_vpc"),
]

_AZURE_RELATIONSHIP_RULES: list[tuple[str, str, str]] = [
    ("azurerm_subnet", "virtual_network_name", "azurerm_virtual_network"),
    ("azurerm_linux_virtual_machine", "network_interface_ids", "azurerm_network_interface"),
    ("azurerm_network_interface", "subnet_id", "azurerm_subnet"),
    ("azurerm_network_security_group", "resource_group_name", "azurerm_resource_group"),
]

_ALL_RULES = _AWS_RELATIONSHIP_RULES + _AZURE_RELATIONSHIP_RULES

# 拡張ルールが利用可能であれば読み込む
try:
    from terrasketch.mapping.extended_resources import (
        EXTENDED_AWS_RELATIONSHIP_RULES,
        EXTENDED_AZURE_RELATIONSHIP_RULES,
    )
    _ALL_RULES = (
        _ALL_RULES
        + EXTENDED_AWS_RELATIONSHIP_RULES
        + EXTENDED_AZURE_RELATIONSHIP_RULES
    )
except ImportError:
    pass


def _build_id_index(resources: list[Resource]) -> dict[str, Resource]:
    """リソースIDからResourceオブジェクトへのインデックスを構築する。"""
    index: dict[str, Resource] = {}
    for r in resources:
        if r.id:
            index[r.id] = r
    return index


def _build_type_index(resources: list[Resource]) -> dict[str, list[Resource]]:
    """リソースタイプからResourceリストへのインデックスを構築する。"""
    index: dict[str, list[Resource]] = {}
    for r in resources:
        index.setdefault(r.type, []).append(r)
    return index


def build_graph(resources: list[Resource]) -> nx.DiGraph:
    """リソース間の依存関係を有向グラフとして構築する。

    エッジは親から子への方向（例: VPC -> Subnet -> EC2）。

    Args:
        resources: パーサーから取得したResourceオブジェクトのリスト。

    Returns:
        リソースアドレスをノードIDとするnetworkx DiGraph。
    """
    graph = nx.DiGraph()
    id_index = _build_id_index(resources)
    type_index = _build_type_index(resources)

    # 全リソースをノードとして追加
    for r in resources:
        graph.add_node(
            r.address,
            resource=r,
            type=r.type,
            label=f"{r.type}\n{r.name}",
        )

    # 関係ルールを適用
    for src_type, attr_name, tgt_type in _ALL_RULES:
        for src in type_index.get(src_type, []):
            attr_value = src.attributes.get(attr_name)
            if attr_value is None:
                continue

            # 単一値とリストの両方に対応
            ref_ids = attr_value if isinstance(attr_value, list) else [attr_value]

            for ref_id in ref_ids:
                if not isinstance(ref_id, str):
                    continue

                # IDで参照先を検索
                target = id_index.get(ref_id)
                if target and target.type == tgt_type:
                    # 親（参照先）から子（参照元）へのエッジ
                    graph.add_edge(target.address, src.address)
                    continue

                # フォールバック: 名前で一致を試みる（Azure等で名前参照を使用する場合）
                for candidate in type_index.get(tgt_type, []):
                    if ref_id in (candidate.name, candidate.attributes.get("name", "")):
                        graph.add_edge(candidate.address, src.address)
                        break

    return graph
